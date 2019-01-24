from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='modbusproxy_cpe_cb',
      version='0.1.0',
      description='A proxy service that converts optimized data send via satellite, to native Modbus slave registers',
      url='https://github.com/Inmarsat/modbusproxy_cpe_cb',
      author='Geoff Bruce-Payne',
      author_email='geoff.bruce-payne@inmarsat.com',
      license='Apache 2.0',
      packages=[
          'modbusproxy_cpe_cb',
      ],
      install_requires=[
          'pymodbus',
          'pyserial',
          'netifaces',
          'clearblade',
          'headless',
          'twisted',
      ],
      include_package_data=True,
      zip_safe=False)
