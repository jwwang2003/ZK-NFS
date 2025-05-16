"""
constants.py
JUN WEI WANG
22302016002
May 14, 2025
"""

# Default NFS server configurations
NFS_SERVER      = 'localhost'
# NFS_PORT      = 2049
NFS_PORT        = 2050
NFS_FS_PORT = 2051

# Default ZooKeeper connection details
ZK_HOST         = 'localhost'
ZK_PORT         = 2181
ZK_LOCK_NODE    = '/nfslk'             # Accordign to lab requirements

# Persistant
PERSIST_DIR = "./persist"