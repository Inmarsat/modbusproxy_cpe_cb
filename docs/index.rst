.. modbusproxy_cpe_cb documentation master file, created by
   sphinx-quickstart on Thu Jan 24 15:48:28 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to modbusproxy_cpe_cb's documentation!
**********************************************

.. toctree::
   :maxdepth: 2
   :caption: Contents:


A proxy service for a `ClearBlade <https://www.clearblade.com/>`_ Edge that takes optimized Modbus slave data
sent via the `Inmarsat <https://www.inmarsat.com/>`_ global satellite network
and re-maps to native Modbus registers for use within a private Enterprise environment.

Uses a secure HTTP connection between the Enterprise and ClearBlade public or private cloud,
running within your LAN environment on private IP addresses.  Data collected from the field runs over
the Inmarsat private network with secure connectivity to the ClearBlade platform.

The solution imports a simple text configuration file of your Modbus RTU/outstation, compatible
with Inmarsat's `IsatData Pro <https://www.inmarsat.com/service/isatdata-pro/>`_ Modbus Proxy application
running on `ORBCOMM <https://www.orbcomm.com>`_ IDP/Lua terminals
such as the `ST6100 <https://www.orbcomm.com/en/hardware/devices/st-series>`_.
You specify the set of registers you want to poll, and optimize the refresh rate plus compress the data
to minimize network costs.  Supplement regular polling with remote analytics and alerts that make sure
you trap relevant events or changes within seconds.  Your SCADA/master can poll within your Enterprise domain
more frequently without missing an event, while getting less critical data in due course.

Reliable, secure, scalable data from your remote field devices anywhere in the world.


modbus_server_adapter
=====================

.. automodule:: modbus_server_adapter

.. argparse::
   :module: modbus_server_adapter
   :func: get_parser
   :prog: modbus_server_adapter.py


context
=======

.. automodule:: context
   :members:


store
=====

.. automodule:: store
   :members:


constants
=========

.. automodule:: constants
   :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
