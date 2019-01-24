"""
Subclasses of the PyModbus data blocks integrated with a ClearBlade Platform.
"""

from clearblade.ClearBladeCore import Query
from constants import *
from pymodbus.datastore.store import ModbusSequentialDataBlock, ModbusSparseDataBlock
from pymodbus.exceptions import ParameterException, NotImplementedException
from pymodbus.compat import iteritems, iterkeys, itervalues, get_next


class CbModbusSequentialDataBlock(ModbusSequentialDataBlock):
    """
    A custom subclass of the sequential data block that includes metadata for the ClearBlade platform context,
    register type, and timestamps of the field data
    """
    def __init__(self, context, register_type, address, values):
        """
        Initializes the sequential datastore

        :param context.ClearBladeModbusProxySlaveContext context: the parent/context of the data block
        :param str register_type: select from hr, ir, di, co
        :param int address: the starting address for the sequential block
        :param iterable values: Either a dictionary or list of values
        """
        super(CbModbusSequentialDataBlock, self).__init__(address=address, values=values)
        self.context = context
        if register_type in REGISTER_TYPES:
            self.register_type = register_type
        else:
            raise ParameterException("Register type must be one of: ".format(REGISTER_TYPES))
        self.timestamps = []
        for i in range(0, len(self.values)-1):
            self.timestamps.append(None)

    def getValues(self, address, count=1):
        """
        Returns the requested values of the datastore

        :param int address: The starting address
        :param int count: The number of values to retrieve
        :returns: The requested values from address:address+count
        :rtype: list
        """
        start = address - self.address
        values, timestamps = read_collection_data(self.context, self.register_type, address, count)
        if len(values) != count:
            self.context.log.warning("Register count mismatch {} requested but {} returned".format(count, len(values)))
            # TODO: WARNING may require a Modbus error to be generated
            count = len(values)
        j = 0
        for i in range(address, address + count):
            self.values[i] = values[j]
            self.timestamps[i] = timestamps[i]
            j += 1
        return self.values[start:start + count]

    def setValues(self, address, values):
        """
        Sets the requested values of the datastore

        :param int address: The starting address
        :param values: The new value(s) to be set, accepts a single int or a list of int
        """
        if not isinstance(values, list):
            values = [values]
        start = address - self.address
        self.values[start:start + len(values)] = values
        for i in range(address, len(values)-1):
            write_collection_data(self.context, self.register_type, address=address + i, data=values[i])

    def get_timestamps(self, address, count=1):
        """
        Returns the timestamps of the field data for the specified registers

        :param int address: the starting address
        :param int count: the number of registers to query
        :returns: timestamps of the requested registers
        :rtype: list of str
        """
        start = address - self.address
        return self.timestamps[start:start + count]


class CbModbusSparseDataBlock(ModbusSparseDataBlock):
    def __init__(self, context, register_type, values):
        """
        Initializes the sparse datastore.
        Using the input values it creates the default datastore value and the starting address

        :param context.ClearBladeModbusProxySlaveContext context: the parent/context of the data block
        :param str register_type: select from hr, ir, di, co
        :param dict values: Either a dictionary or list of values
        """
        super(CbModbusSparseDataBlock, self).__init__(values=values)
        self.context = context
        if register_type in REGISTER_TYPES:
            self.register_type = register_type
        else:
            raise ParameterException("Register type must be one of: ".format(REGISTER_TYPES))
        self.timestamps = {}
        for addr in self.values:
            self.timestamps[addr] = None

    def getValues(self, address, count=1):
        """
        Returns the requested values of the datastore

        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        """
        values, timestamps = read_collection_data(self.context, self.register_type, address, count)
        if len(values) != count:
            self.context.log.warning("Register count mismatch {} requested but {} returned".format(count, len(values)))
        for key in values:
            for addr in self.values:
                if key == addr:
                    self.values[addr] = values[key]
                    self.timestamps[addr] = timestamps[key]
        # TODO: this sends back auto-filled registers that aren't in the sparse definition but should probably throw
        #       a Modbus error
        return [self.values[i] for i in range(address, address + count)]

    def setValues(self, address, values):
        """
        Sets the requested values of the datastore

        :param address: The starting address
        :param values: The new values to be set
        """
        if isinstance(values, dict):
            for idx, val in iteritems(values):
                self.values[idx] = val
                # TODO: may be a more efficient way than multiple calls to the ClearBlade API (one per index)
                write_collection_data(self.context, self.register_type, address=idx, data=val)
        else:
            if not isinstance(values, list):
                values = [values]
            for idx, val in enumerate(values):
                self.values[address + idx] = val
                write_collection_data(self.context, self.register_type, address=address + idx, data=val)

    def get_timestamps(self, address, count=1):
        """
        Returns the timestamps of the field data for the specified registers

        :param int address: the starting address
        :param int count: the number of registers to query
        :returns: timestamps of the requested registers in the format {address: timestamp}
        :rtype: dict of str
        """
        return [self.timestamps[i] for i in range(address, address + count)]


def read_collection_data(context, register_type, address, count, fill=0):
    """
    Retrieve data from the specified collection.
    When retrieving sequential blocks if the ClearBlade collection is missing registers between the start and end,
    those will be filled (optionally)

    :param context.ClearBladeModbusProxySlaveContext context: The ClearBlade parent metadata to query against.
    :param str register_type: the type of register ('co', 'di', 'hr', 'ir')
    :param int address: The starting address
    :param int count: The number of values to retrieve
    :param int fill: automatically fills gaps in sequential register blocks with this value (or None)
    :returns: values, timestamps of the data read from the ClearBlade collection/proxy
    :rtype: list or dict (sequential or sparse)
    """
    collection = context.cb_system.Collection(context.cb_auth, collectionName=context.cb_data_collection)
    query = Query()
    query.equalTo(COL_PROXY_IP_ADDRESS, context.ip_proxy)
    query.equalTo(COL_SLAVE_ID, context.slave_id)
    query.equalTo(COL_REG_TYPE, register_type)
    if count > 1:
        query.greaterThanEqualTo(COL_REG_ADDRESS, address)
        query.lessThan(COL_REG_ADDRESS, address + count)
    else:
        query.equalTo(COL_REG_ADDRESS, address)
    reg_list = sorted(collection.getItems(query), key=lambda k: k[COL_REG_ADDRESS])
    if len(reg_list) != count:
        context.log.warning("Got {} rows from ClearBlade, expecting {} registers".format(len(reg_list), count))
    if context.sparse:
        values = {}
        timestamps = {}
        # Below commented code would fill in missing registers in a sparse data block (placeholder needs more thought)
        # for i in range(0, count-1):
        #     curr_addr = reg_list[i][COL_REG_ADDRESS]
        #     values[curr_addr] = reg_list[i][COL_REG_DATA]
        #     if i+1 < count and i+1 < len(reg_list):
        #         next_addr = curr_addr + 1
        #         if reg_list[i+1][COL_REG_ADDRESS] != next_addr and fill:
        #             context.log.info("Filling {} register {} with value {}"
        #                              .format(register_type, next_addr, FILL_VALUE))
        #             values[next_addr] = FILL_VALUE
        for reg in reg_list:
            values[reg[COL_REG_ADDRESS]] = reg[COL_REG_DATA]
            timestamps[reg[COL_REG_ADDRESS]] = reg[COL_DATA_TIMESTAMP]
    else:
        values = []
        timestamps = []
        for addr in range(address, address + count):
            if reg_list[addr][COL_REG_ADDRESS] != addr:
                if fill is not None:
                    if isinstance(fill, int):
                        context.log.info("Filling {} register {} with value {}".format(register_type, addr, fill))
                        reg_list.insert(addr, {COL_REG_DATA: fill})
                    else:
                        raise ValueError("Fill parameter must be integer or None")
                else:
                    raise ParameterException("ClearBlade Collection missing register {} from block [{}:{}]"
                                             .format(addr, address, address + count))
            values.append(reg_list[addr][COL_REG_DATA])
            timestamps.append(reg_list[addr][COL_DATA_TIMESTAMP])
    return values, timestamps


def write_collection_data(context, register_type, address, data):
    """
    Retrieve input register values from the Analog_Input_Registers collection

    :param context.ClearBladeModbusProxySlaveContext context: The ClearBlade parent metadata to query against.
    :param str register_type: the type of register (co, di, hr, ir)
    :param int address: The starting address
    :param data: The data value(s) to write
    """
    collection = context.cb_system.Collection(context.cb_auth, collectionName=context.cb_data_collection)
    query = Query()
    query.equalTo(COL_PROXY_IP_ADDRESS, context.ip_proxy)
    query.equalTo(COL_SLAVE_ID, context.slave_id)
    query.equalTo(COL_REG_TYPE, register_type)
    query.equalTo(COL_REG_ADDRESS, address)
    collection.updateItems(query, {COL_REG_DATA: data})
    # TODO: error handling in case of write error, update data timestamp?
