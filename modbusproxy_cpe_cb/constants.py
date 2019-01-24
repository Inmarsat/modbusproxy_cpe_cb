"""
A set of constants used in the ClearBlade platform Collections
and the Modbus Proxy Lua service ``config.dat`` file.
"""

ADAPTER_DEVICE_ID = 'ModbusProxyServerAdapter'
ADAPTER_CONFIG_COLLECTION = 'NotImplemented'

TYPE_HOLDING_REGISTER = 'hr'
TYPE_INPUT_REGISTER = 'ir'
TYPE_DISCRETE_INPUT = 'di'
TYPE_COIL = 'co'
REGISTER_TYPES = [TYPE_HOLDING_REGISTER, TYPE_INPUT_REGISTER, TYPE_DISCRETE_INPUT, TYPE_COIL]


# ---------- ClearBlade platform RTU Configuraion Collection & Columns (minimum required) ---------- #
DEVICE_PROXY_CONFIG_COLLECTION = 'ModbusProxyRtus'
COL_PROXY_IP_ADDRESS = 'ip_address'
COL_PROXY_IP_PORT = 'ip_port'
COL_SLAVE_ID = 'slave_id'
COL_PROXY_CONFIG_FILE = 'config_file'
COL_PROXY_TIMESTAMP = 'last_report_time'


# ---------- ClearBlade platform Data Collection & Columns (minimum required) ---------------------- #
DATA_COLLECTION = 'ModbusProxyData'
# COL_PROXY_IP_ADDRESS must match above
# COL_PROXY_IP_PORT must match above
# COL_SLAVE_ID must match above
COL_REG_ADDRESS = 'register_address'
COL_REG_DATA = 'register_data'
COL_DATA_TIMESTAMP = 'timestamp'
COL_REG_TYPE = 'register_type'


# ---------- ModbusProxy Lua service tags/labels used in the config.dat file ----------------------- #
TEMPLATE_PARSER_DESC = '/*DEVICE;'
# TEMPLATE_PARSER_PORT = "port"   # Not used for local polling, this applies only to the physical RTU
TEMPLATE_PARSER_NETWORK = 'deviceId'
# TEMPLATE_PARSER_REG_DESC = "/*REGISTER"   # Not used for proxy polling, applies to RTU simulator only
TEMPLATE_PARSER_REGISTER_DEF = 'paramId'
TEMPLATE_PARSER_REG_UID = 'paramId'
TEMPLATE_PARSER_REG_ADDRESS = 'address'
TEMPLATE_PARSER_SEPARATOR = ';'
TEMPLATE_PARSER_SLAVE_ID = 'networkId'
TEMPLATE_PARSER_NOT_ZERO_MODE = 'plcBaseAddress'   # Note: this PLC Base Address is NOT (opposite of) zero_mode
TEMPLATE_PARSER_SPARSE_MODE = 'sparse'
TEMPLATE_PARSER_REG_TYPE = 'registerType'
TEMPLATE_PARSER_TYPE_HOLDING_REGISTER = 'holding'
TEMPLATE_PARSER_TYPE_INPUT_REGISTER = 'analog'
TEMPLATE_PARSER_TYPE_DISCRETE_INPUT = 'input'
TEMPLATE_PARSER_TYPE_COIL = 'coil'
