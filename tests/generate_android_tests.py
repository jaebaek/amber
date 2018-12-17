#!/usr/bin/env python
# Copyright 2018 The Amber Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import optparse
import os
import re
import shutil
import subprocess
import sys
import tempfile


class TestGenerator:
  def GenerateTest(self, tc):
    print "Generating Android shaders for %s" % tc

    cmd = [self.options.amber_path, '--dump-shaders', tc]

    try:
      err = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
      if err != "":
        sys.stdout.write(err)
        return

    except Exception as e:
      print e.output
      print e
      return

    return

  def GenerateTests(self):
    for tc in self.test_cases:
      self.GenerateTest(tc)

  def Generate(self):
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    usage = 'usage: %prog [options] (file)'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--test-dir',
                      default=os.path.join(os.path.dirname(__file__), 'cases'),
                      help='path to directory containing test files')
    parser.add_option('--amber-path',
                      default=os.path.join(base_path, 'out', 'Debug', 'amber'),
                      help='path to Amber binary')
    parser.add_option('--output-dir', default=None,
                      help='path to directory for output scripts and shaders')
    parser.add_option('--force-output',
                      default=False,
                      action='store_true',
                      help='''force to output scripts and shaders even though
                      they already exist in the output directory''')

    self.options, self.args = parser.parse_args()

    if not os.path.isfile(self.options.amber_path):
      print "--amber-path must point to an Amber executable"
      return 1

    input_file_re = re.compile('^.+[.]amber')
    self.test_cases = []
    self.temp_dir = tempfile.mkdtemp() if self.options.output_dir else None

    if self.args:
      for filename in self.args:
        input_path = os.path.join(self.options.test_dir, filename)
        if self.temp_dir:
          shutil.copy(input_path, self.temp_dir)
          input_path = os.path.join(self.temp_dir, filename)

        if not os.path.isfile(input_path):
          print "Cannot find test file '%s'" % filename
          return 1

        self.test_cases.append(input_path)

    else:
      root_dir = self.options.test_dir
      if self.temp_dir:
        for file_or_dir in os.listdir(root_dir):
          file_or_dir_path = os.path.join(root_dir, file_or_dir)
          if os.path.isfile(file_or_dir_path):
            shutil.copy(file_or_dir_path, self.temp_dir)
          else:
            shutil.copytree(file_or_dir_path, self.temp_dir)

        root_dir = self.temp_dir

      for file_dir, _, filename_list in os.walk(root_dir):
        for input_filename in filename_list:
          if input_file_re.match(input_filename):
            input_path = os.path.join(file_dir, input_filename)
            if os.path.isfile(input_path):
              self.test_cases.append(input_path)

    self.GenerateTests()

    if self.temp_dir:
      for file_or_dir in os.listdir(self.temp_dir):
        output_path = os.path.join(self.options.output_dir, file_or_dir)
        if os.path.isfile(output_path):
          if not self.options.force_output:
            continue

          os.remove(output_path)

        if os.path.isdir(output_path):
          if not self.options.force_output:
            continue

          os.rmtree(output_path)

        shutil.move(os.path.join(self.temp_dir, file_or_dir),
                    self.options.output_dir)

      shutil.rmtree(self.temp_dir)

    return 0


def main():
  android_test_generator = TestGenerator()
  return android_test_generator.Generate()


if __name__ == '__main__':
  sys.exit(main())
