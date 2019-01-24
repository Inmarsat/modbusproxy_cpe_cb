"""
Establishes a PyModbus server/slave context that maps to ClearBlade platform collections.
Requires a unique instance per slave device represented in the platform.
"""

from clearblade.ClearBladeCore import Query
from pymodbus.interfaces import IModbusSlaveContext
from pymodbus.datastore.context import ModbusServerContext
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.constants import Endian

from headless import is_logger, get_wrapping_logger
from store import CbModbusSequentialDataBlock, CbModbusSparseDataBlock
from constants import *


class ClearBladeModbusProxySlaveContext(IModbusSlaveContext):
    """
    A Modbus slave context integrated with ClearBlade, derived from an Inmarsat IDP Modbus Proxy template file.
    Represents a single remote outstation / RTU

    The ClearBlade collection must have a row defining at least the following:

       * ``ip_address`` (str) the proxy address (IPv4) assigned to the remote outstation/RTU
       * ``ip_port`` (int) the (TCP) port of the proxy address for the RTU
       * ``slave_id`` (int) the Modbus Slave ID / Unit ID (0..254)
       * ``zero_mode`` (bool)
       * ``last_report_time`` (ts) timestamp of the most recently received data from the RTU in the field (metadata)
       * ``config_file`` (str) a formatted text file conforming to Inmarsat's IDP Modbus Proxy template

    .. todo::
       Add URL link to Modbus Proxy template

    """
    def __init__(self, server_context, config, **kwargs):
        """

        :param ClearBladeModbusProxyServerContext server_context: the parent server context
        :param dict config: a row returned from reading the Clearblade collection for RTU configuration
        :param kwargs: optional arguments such as log
        """
        if is_logger(kwargs.get('log', None)):
            self.log = kwargs.get('log')
        else:
            self.log = get_wrapping_logger(name='ClearBladeModbusSlaveContext',
                                           debug=True if kwargs.get('debug', None) else False)
        self.cb_system = server_context.cb_system
        self.cb_auth = server_context.cb_auth
        self.cb_data_collection = server_context.cb_data
        self.ip_proxy = str(config[COL_PROXY_IP_ADDRESS])
        self.ip_port = int(config[COL_PROXY_IP_PORT])
        if self.ip_proxy == '':
            self.log.warning("No proxy IP address specified, may result in conflicting slave_id")
        self.slave_id = int(config[COL_SLAVE_ID])
        self.zero_mode = True
        # self.last_report_time = config[COL_PROXY_TIMESTAMP]
        self.identity = ModbusDeviceIdentification()
        self.sparse = False
        self.store = dict()
        # Byte order and word order may be per-register and are assumed to be handled by the Polling Client
        # self.byteorder = Endian.Big
        # self.wordorder = Endian.Big
        self._parse_config(config[COL_PROXY_CONFIG_FILE])
        self.log.debug("Slave context {} complete".format(self.ip_proxy))

    def _parse_config(self, config_file):
        """Parses the ``config.dat`` file"""
        registers = []
        lines = config_file.splitlines()
        for line in lines:
            if line[0:len(TEMPLATE_PARSER_DESC)] == TEMPLATE_PARSER_DESC:
                identity = line.split(TEMPLATE_PARSER_SEPARATOR)
                for id_tag in identity:
                    if id_tag[0:len('VendorName')] == 'VendorName':
                        self.identity.VendorName = id_tag[len('VendorName') + 1:].strip()
                    elif id_tag[0:len('ProductCode')] == 'ProductCode':
                        self.identity.ProductCode = id_tag[len('ProductCode') + 1:].strip()
                    elif id_tag[0:len('VendorUrl')] == 'VendorUrl':
                        self.identity.VendorUrl = id_tag[len('VendorUrl') + 1:].strip()
                    elif id_tag[0:len('ProductName')] == 'ProductName':
                        self.identity.ProductName = id_tag[len('ProductName') + 1:].strip()
                    elif id_tag[0:len('ModelName')] == 'ModelName':
                        self.identity.ModelName = id_tag[len('ModelName') + 1:].strip()
                    elif id_tag[0:len('MajorMinorRevision')] == 'MajorMinorRevision':
                        self.identity.MajorMinorRevision = id_tag[len('MajorMinorRevision') + 1:].strip()
                    elif id_tag[0:len('sparse')].lower() == 'sparse':
                        self.sparse = bool(int(id_tag[len('sparse') + 1:].strip()))
            elif line[0:len(TEMPLATE_PARSER_NETWORK)] == TEMPLATE_PARSER_NETWORK:
                net_info = line.split(TEMPLATE_PARSER_SEPARATOR)
                for i in net_info:
                    if i[0:len(TEMPLATE_PARSER_SLAVE_ID)] == TEMPLATE_PARSER_SLAVE_ID:
                        net_id = int(i[len(TEMPLATE_PARSER_SLAVE_ID) + 1:].strip())
                        if net_id in range(1, 255):
                            self.slave_id = int(i[len(TEMPLATE_PARSER_SLAVE_ID) + 1:])
                        else:
                            self.log.error("Invalid Modbus Slave ID {id}".format(id=net_id))
                    elif i[0:len(TEMPLATE_PARSER_NOT_ZERO_MODE)] == TEMPLATE_PARSER_NOT_ZERO_MODE:
                        plc = int(i[len(TEMPLATE_PARSER_NOT_ZERO_MODE) + 1:].strip())
                        self.zero_mode = False if plc == 1 else True
                    # Byte order and word order may be per-register and are assumed to be handled by the Polling Client
                    # elif i[0:len('byteOrder')] == 'byteOrder':
                    #     self.byteorder = Endian.Big if i[len('byteOrder') + 1:].strip() == 'msb' else Endian.Little
                    # elif i[0:len('wordOrder')] == 'wordOrder':
                    #     self.wordorder = Endian.Big if i[len('wordOrder') + 1:].strip() == 'msw' else Endian.Little
            elif line[0:len(TEMPLATE_PARSER_REGISTER_DEF)] == TEMPLATE_PARSER_REGISTER_DEF:
                # TODO: handle multi-register blocks
                reg_config = line.split(TEMPLATE_PARSER_SEPARATOR)
                reg_exists = False
                this_reg = None
                for c in reg_config:
                    if c[0:len(TEMPLATE_PARSER_REG_UID)] == TEMPLATE_PARSER_REG_UID:
                        param_id = int(c[len(TEMPLATE_PARSER_REG_UID) + 1:].strip())
                        for reg in registers:
                            if param_id == reg.param_id:
                                reg_exists = True
                        if not reg_exists:
                            registers.append(self._RegisterBlockConfig(param_id=param_id))
                            reg_exists = True
                        this_reg = param_id
                    elif c[0:len(TEMPLATE_PARSER_REG_ADDRESS)] == TEMPLATE_PARSER_REG_ADDRESS:
                        addr = int(c[len(TEMPLATE_PARSER_REG_ADDRESS) + 1:].strip())
                        # TODO: confirm this works properly
                        if not self.zero_mode:
                            addr += 1
                        if addr in range(0, 99999+1):
                            for reg in registers:
                                if reg.param_id == this_reg:
                                    reg.address = addr
                            if not reg_exists:
                                registers.append(self._RegisterBlockConfig(address=addr))
                                reg_exists = True
                        else:
                            self.log.error("Invalid Modbus address {num}".format(num=addr))
                    elif c[0:len(TEMPLATE_PARSER_REG_TYPE)] == TEMPLATE_PARSER_REG_TYPE:
                        reg_type = c[len(TEMPLATE_PARSER_REG_TYPE) + 1:].strip()
                        if reg_type in [TEMPLATE_PARSER_TYPE_INPUT_REGISTER]:
                            for reg in registers:
                                if reg.param_id == this_reg:
                                    reg.register_type = TYPE_INPUT_REGISTER
                        elif reg_type in [TEMPLATE_PARSER_TYPE_HOLDING_REGISTER]:
                            for reg in registers:
                                if reg.param_id == this_reg:
                                    reg.register_type = TYPE_HOLDING_REGISTER
                        elif reg_type in [TEMPLATE_PARSER_TYPE_DISCRETE_INPUT]:
                            for reg in registers:
                                if reg.param_id == this_reg:
                                    reg.register_type = TYPE_DISCRETE_INPUT
                        elif reg_type in [TEMPLATE_PARSER_TYPE_COIL]:
                            for reg in registers:
                                if reg.param_id == this_reg:
                                    reg.register_type = TYPE_COIL
                        else:
                            self.log.error("Unsupported registerType {}".format(reg_type))
        hr_sparse_block = {}
        ir_sparse_block = {}
        di_sparse_block = {}
        co_sparse_block = {}
        hr_sequential = []
        ir_sequential = []
        di_sequential = []
        co_sequential = []
        for reg in registers:
            if reg.register_type == TYPE_HOLDING_REGISTER:
                if self.sparse:
                    hr_sparse_block[reg.address] = 0
                else:
                    hr_sequential.append(reg.address)
            elif reg.register_type == TYPE_INPUT_REGISTER:
                if self.sparse:
                    ir_sparse_block[reg.address] = 0
                else:
                    ir_sequential.append(reg.address)
            elif reg.register_type == TYPE_DISCRETE_INPUT:
                if self.sparse:
                    di_sparse_block[reg.address] = 0
                else:   # reg.register_type == TYPE_COIL
                    di_sequential.append(reg.address)
            else:
                if self.sparse:
                    co_sparse_block[reg.address] = 0
                else:
                    co_sequential.append(reg.address)
        if self.sparse:
            self.store['h'] = self._setup_sparse_block(hr_sparse_block, TYPE_HOLDING_REGISTER)
            self.store['i'] = self._setup_sparse_block(ir_sparse_block, TYPE_INPUT_REGISTER)
            self.store['d'] = self._setup_sparse_block(di_sparse_block, TYPE_DISCRETE_INPUT)
            self.store['c'] = self._setup_sparse_block(co_sparse_block, TYPE_COIL)
        else:
            self.store['h'] = self._setup_sequential_block(hr_sequential, TYPE_HOLDING_REGISTER)
            self.store['i'] = self._setup_sequential_block(ir_sequential, TYPE_INPUT_REGISTER)
            self.store['d'] = self._setup_sequential_block(di_sequential, TYPE_DISCRETE_INPUT)
            self.store['c'] = self._setup_sequential_block(co_sequential, TYPE_COIL)

    def _setup_sparse_block(self, block, register_type):
        """
        Sets up a custom ModbusSparseDataBlock for ClearBlade interaction and metadata

        :param dict block: a dictionary mapped as {address: value}
        :param str register_type: the type of register / memory value ['di', 'co', 'hr', 'ir']
        :return: a ModbusDataBlock
        :rtype: CbModbusSparseDataBlock or None
        """
        if register_type in REGISTER_TYPES and len(block) > 0:
            return CbModbusSparseDataBlock(context=self, register_type=register_type, values=block)
        else:
            return None

    def _setup_sequential_block(self, block, register_type):
        """
        Sets up a custom ModbusSequentialDataBlock for ClearBlade interaction and metadata

        :param list block: a list of contiguous register addresses starting from a base address
        :param str register_type: the type of register / memory value ['di', 'co', 'hr', 'ir']
        :return: a ModbusDataBlock
        :rtype: CbModbusSequentialDataBlock or None
        """
        if register_type in REGISTER_TYPES and len(block) > 0:
            block.sort()
            return CbModbusSequentialDataBlock(context=self, register_type=register_type,
                                               address=block[0],
                                               values=[0 for x in range(block[0], block[len(block)-1])])
        else:
            return None

    class _RegisterBlockConfig(object):
        """Private class for parsing of register block metadata"""
        def __init__(self, param_id=None, address=None, register_type=None, block_size=1):
            """
            Initialize termporary metadata for parsing

            :param int param_id: A unique parameterId defined on the Modbus Proxy remote edge device
            :param int address: the starting address of the block
            :param str register_type: the type of data 'di', 'co', 'hr', 'ir'
            :param int block_size: (optional) for specifying blocks that span multiple registers (unused)
            """
            self.param_id = param_id
            self.address = address
            self.register_type = register_type
            self.block_size = block_size

    def __str__(self):
        """
        Returns a string representation of the context
        """
        return "ClearBlade Modbus Proxy Slave Context"

    def reset(self):
        """ NOT IMPLEMENTED - placeholder for future """
        # No-op for this implementation
        self.log.warning("Reset requested but no-operation due to complex proxy operation")

    def validate(self, fx, address, count=1):
        """
        Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        """
        if not self.zero_mode:
            address = address + 1
        self.log.debug("validate[{}] {}:{}".format(fx, address, count))
        return self.store[self.decode(fx)].validate(address, count)

    def getValues(self, fx, address, count=1):
        """
        Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from address:address+count
        """
        if not self.zero_mode:
            address = address + 1
        self.log.debug("getValues[{}] {}:{}".format(fx, address, count))
        return self.store[self.decode(fx)].getValues(address, count)

    def setValues(self, fx, address, values):
        """
        Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        """
        if not self.zero_mode:
            address = address + 1
        self.log.debug("setValues[{}] {}:{}".format(fx, address, len(values)))
        self.store[self.decode(fx)].setValues(address, values)


class ClearBladeModbusProxyServerContext(ModbusServerContext):
    """
    A Modbus server context, initialized by reading a ClearBlade collection defining Slave configurations / templates
    """

    def __init__(self, cb_system, cb_auth, cb_slaves_config, cb_data, **kwargs):
        """
        Initialize the Server context

        :param clearblade.ClearBladeCore.System cb_system: a ClearBlade System
        :param clearblade.ClearBladeCore.Device cb_auth: a ClearBlade authenticated Device
        :param str cb_slaves_config: the name of the ClearBlade Collection holding Slave definitions
        :param str cb_data: the name of the ClearBlade Collection holding data
        :param kwargs: optionally takes log definition
        """
        super(ClearBladeModbusProxyServerContext, self).__init__(single=kwargs.get('single', False))
        if is_logger(kwargs.get('log', None)):
            self.log = kwargs.get('log')
        else:
            self.log = get_wrapping_logger(name='ClearBladeModbusServerContext',
                                           debug=True if kwargs.get('debug', None) else False)
        self.cb_system = cb_system
        self.cb_auth = cb_auth
        self.ip_address = kwargs.get('ip_address', None)
        self.cb_slaves = cb_slaves_config
        self.cb_data = cb_data
        self._initialize_slaves()

    def _initialize_slaves(self):
        """Sets up the slave contexts for the server"""
        slaves = []
        collection = self.cb_system.Collection(self.cb_auth, collectionName=self.cb_slaves)
        query = Query()
        if self.ip_address is not None:
            self.log.debug("Querying ClearBlade based on ip_address: {}".format(self.ip_address))
            query.equalTo(COL_PROXY_IP_ADDRESS, self.ip_address)
        else:
            self.log.debug("No ip_address found in ClearBlade, querying based on non-empty slave_id")
            query.notEqualTo(COL_SLAVE_ID, '')
        rows = collection.getItems(query)
        self.log.debug("Found {} rows in ClearBlade adapter config".format(len(rows)))
        for row in rows:
            slave_id = int(row[COL_SLAVE_ID])
            if slave_id not in slaves:
                slaves.append(slave_id)
                self[slave_id] = ClearBladeModbusProxySlaveContext(server_context=self, config=row, log=self.log)
            else:
                self.log.warning("Duplicate slave_id {} found in RTUs collection - only 1 RTU per server context"
                                 .format(slave_id))
