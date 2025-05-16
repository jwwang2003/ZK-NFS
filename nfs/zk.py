from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError, KazooException
from typing import Optional

from nfs.constants import ZK_HOST, ZK_PORT, ZK_LOCK_NODE

class ZooKeeperManager:
    def __init__(self, host: str = ZK_HOST, port: int = ZK_PORT) -> None:
        """Initialize the ZooKeeperManager with the given host and port."""
        self.zk_host: str = host
        self.zk_port: int = port
        self.zk: Optional[KazooClient] = None
        self.lock_node: str = ZK_LOCK_NODE # '/nfslk'
    
    # Basic methods
    def start(self) -> None:
        """Start the connection to Zookeeper."""
        try:
            self.zk = KazooClient(hosts=f'{self.zk_host}:{self.zk_port}')
            self.zk.start()
            print(f"Connected to Zookeeper at {self.zk_host}:{self.zk_port}")
        except KazooException as e:
            print(f"Failed to connect to Zookeeper: {e}")
            self.zk = None

    def stop(self) -> None:
        """Stop the connection to Zookeeper."""
        if self.zk:
            self.zk.stop()
            self.zk.close()
            print("Disconnected from Zookeeper")

    def acquire_lock(self) -> bool:
        """Acquire a lock by creating an ephemeral node in Zookeeper."""
        if not self.zk:
            print("Zookeeper connection is not established. Cannot acquire lock.")
            return False
        try:
            # Ensure the lock node exists, create the ephemeral lock node
            self.zk.ensure_path(self.lock_node)
            self.zk.create(self.lock_node, b"", ephemeral=True)
            print("Lock acquired!")
            return True
        except NodeExistsError:
            print("Lock already exists. Unable to acquire lock.")
            return False
        except KazooException as e:
            print(f"Error acquiring lock: {e}")
            return False

    def release_lock(self) -> bool:
        """Release the lock by deleting the lock node in Zookeeper."""
        if not self.zk:
            print("Zookeeper connection is not established. Cannot release lock.")
            return False
        try:
            self.zk.delete(self.lock_node)
            print("Lock released!")
            return True
        except KazooException as e:
            print(f"Error releasing lock: {e}")
            return False

    def is_locked(self) -> bool:
        """Check if the lock node exists."""
        if not self.zk:
            print("Zookeeper connection is not established.")
            return False
        try:
            # Check if the lock node exists
            if self.zk.exists(self.lock_node):
                print("Lock exists.")
                return True
            else:
                print("Lock does not exist.")
                return False
        except KazooException as e:
            print(f"Error checking lock: {e}")
            return False
