import os

py_files = [r'sht30', r'mqtt_as']

for py_file in py_files:
    os.system('../../micropython-master/mpy-cross/mpy-cross {}.py'.format(py_file))
