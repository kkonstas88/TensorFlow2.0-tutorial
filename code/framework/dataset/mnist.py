"""Mnist dataset preprocessing and specifications."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gzip
import matplotlib.pyplot as plt
import numpy as np
import os
from six.moves import urllib
import struct
import sys
import tensorflow as tf

from common import utils

REMOTE_URL = "http://yann.lecun.com/exdb/mnist/"
LOCAL_DIR = os.path.join("data/mnist/")
TRAIN_IMAGE_URL = "train-images-idx3-ubyte.gz"
TRAIN_LABEL_URL = "train-labels-idx1-ubyte.gz"
TEST_IMAGE_URL = "t10k-images-idx3-ubyte.gz"
TEST_LABEL_URL = "t10k-labels-idx1-ubyte.gz"

IMAGE_SIZE = 28
NUM_CLASSES = 10

HPARAMS = {
  "image_size": IMAGE_SIZE,
  "num_classes": NUM_CLASSES,
}


def get_split(split):
  """Returns train/test split paths."""
  output_data = os.path.join(LOCAL_DIR, "data_%s.tfrecord" % split)
  return output_data


def create(split):
  """Create an instance of the dataset object."""
  return tf.contrib.data.TFRecordDataset(get_split(split))


def parser_fn(record):
  """Parse input record to features and labels."""
  features = tf.parse_single_example(record, {
    "image": tf.FixedLenFeature([], tf.string),
    "label": tf.FixedLenFeature([], tf.int64),
  })

  image = tf.to_float(tf.image.decode_image(features["image"], 1)) / 255.0
  image = tf.reshape(image, [IMAGE_SIZE, IMAGE_SIZE, 1])
  label = features["label"]

  return {"image": image}, {"label": label}


def _download_data():
  """Download the MNIST dataset."""
  if not os.path.exists(LOCAL_DIR):
    os.makedirs(LOCAL_DIR)
  for name in [
    TRAIN_IMAGE_URL,
    TRAIN_LABEL_URL,
    TEST_IMAGE_URL,
    TEST_LABEL_URL]:
    if not os.path.exists(LOCAL_DIR + name):
      urllib.request.urlretrieve(REMOTE_URL + name, LOCAL_DIR + name)


def _image_iterator(split):
  """An iterator that reads and returns images and labels from MNIST."""
  image_urls = {
    tf.estimator.ModeKeys.TRAIN: TRAIN_IMAGE_URL,
    tf.estimator.ModeKeys.EVAL: TEST_IMAGE_URL
  }[split]
  label_urls = {
    tf.estimator.ModeKeys.TRAIN: TRAIN_LABEL_URL,
    tf.estimator.ModeKeys.EVAL: TEST_LABEL_URL
  }[split]

  with gzip.open(LOCAL_DIR + image_urls, "rb") as f:
    magic, num, rows, cols = struct.unpack(">IIII", f.read(16))
    images = np.frombuffer(f.read(num * rows * cols), dtype=np.uint8)
    images = np.reshape(images, [num, rows, cols])
    print("Loaded %d images of size [%d, %d]." % (num, rows, cols))

  with gzip.open(LOCAL_DIR + label_urls, "rb") as f:
    magic, num = struct.unpack(">II", f.read(8))
    labels = np.frombuffer(f.read(num), dtype=np.int8)
    print("Loaded %d labels." % num)

  for i in range(num):
    yield utils.encode_image(images[i]), labels[i]


def _convert_data(split):
  """Convert the dataset to TFRecord format."""
  def _create_example(item):
    image, label = item
    example = tf.train.Example(features=tf.train.Features(
      feature={
        "image": tf.train.Feature(
          bytes_list=tf.train.BytesList(value=[image])),
        "label": tf.train.Feature(
          int64_list=tf.train.Int64List(value=[label.astype(np.int64)]))
      }))
    return example

  utils.parallel_record_writer(
    _image_iterator(split), _create_example, get_split(split))


def _visulize_data(split=tf.estimator.ModeKeys.TRAIN):
  """Read an visualize the first example form the dataset."""
  path = get_split(split)
  iterator = tf.python_io.tf_record_iterator(path)
  item = next(iterator)

  example = tf.train.Example()
  example.ParseFromString(item)

  image = utils.decode_image(
    example.features.feature["image"].bytes_list.value[0])
  label = example.features.feature["label"].int64_list.value[0]

  plt.imshow(image.squeeze())
  plt.title("Label: %d" % label)
  plt.show()


if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Usage: python dataset.mnist <convert|visualize>")
    sys.exit(1)

  if sys.argv[1] == "convert":
    _download_data()
    _convert_data(tf.estimator.ModeKeys.TRAIN)
    _convert_data(tf.estimator.ModeKeys.EVAL)
  elif sys.argv[1] == "visualize":
    _visulize_data()
  else:
    print("Unknown command", sys.argv[1])
