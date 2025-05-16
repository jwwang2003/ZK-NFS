import os
import argparse
import asyncio
import websockets
import shlex
import tempfile
import readline
from termcolor import colored, cprint
from pathlib import Path
from kazoo.client import KazooClient, Lock
from typing import Callable, Optional

from nfs.fs import FileNode
from nfs.packet import OpenRequest, OpenResponse, \
    CloseRequest, CloseResponse, \
    ReadRequest, ReadResponse, \
    WriteRequest, WriteResponse
from nfs.constants import NFS_SERVER, NFS_PORT, NFS_FS_PORT, ZK_HOST

# Global WebSocket connection variables
nfs_server_uri = f"ws://{NFS_SERVER}:{NFS_PORT}"
file_transfer_server_uri = f"ws://{NFS_SERVER}:{NFS_FS_PORT}"

HISTORY_FILE = "nfs_client_history.txt"

class Command:
    def __init__(
        self, 
        name: str,
        formal: str,
        usage: str,
        description: str, 
        handler: Callable[..., None], 
        callback: Optional[Callable[..., None]] = None
    ):
        """
        Initializes the Command object with the command details.
        
        :param name: The shorthand or alias for the command (e.g., 'open', 'close').
        :param formal_name: A more descriptive or formal name for the command (e.g., 'Open a file').
        :param description: A brief description of what the command does.
        :param handler: The function that handles the command logic.
        :param callback: (optional) An additional callback function after execution (if needed).
        :param help_message: (optional) A detailed help message for the command.
        """
        self.name: str = name
        self.formal: str = formal
        self.usage: str = usage
        self.description: str = description
        self.handler: Callable[..., None] = handler
        self.callback: Optional[Callable[..., None]] = callback
    
    def get_descriptor(self):
        return f"{self.name} ({self.formal}): {self.usage}"
    
    def print_help(self):
        print(self.get_help_msg())
    
    def get_help_msg(self):
        return \
f"""
{self.formal} ({self.name}):
    Usage: {self.usage}
    {self.description}"""

class NFSClient:
    '''
    <h1>NFS Client</h1>
    A simple network file system implemented by yours truely.</br>
    JUN WEI WANG 22302016002
    
    <h2>Features</h2>
    <ul>
        <li>`open`, `close`, `read`, `write`, `delete`</li>
        <li>File locks via ZooKeeper</li>
        <li>Partial reads & writes (with offsets)</li>
        <li>File deletion</li>
        <li>Automatic folder deletion (if empty)</li>
    </ul>
    
    <h2>Important notes:</h2>
    <ul>
        <li>Only one file can be opened at once (simplifies design & implementation)</li>
        <li>One client only needs to keep track of one lock</li>
    </ul>
    '''
    
    def __init__(self, host, port, binary_port, zk_host):
        self.host = host
        self.port = port
        self.binary_port = binary_port
        self.zk_host = zk_host
        
        self.zk = KazooClient(hosts=zk_host)
        self.zk.start()
        
        # Tracking the opened file
        self.current_file_node: FileNode = None
        self.current_zk_lock: Lock = None
        
        # Init a temporary folder (to store the cached file)
        self.temp_folder = tempfile.mkdtemp(prefix="buf")
        self.temp_file: Path = None
        
        # Set up the commands
        self.commands = [
            Command(
                name="open",
                formal="Open a File",
                usage="open <file_path>",
                description="This command opens a specified file on the server. Provide the file path of the file you wish to open.",
                handler=self.handle_open
            ),
            Command(
                name="close",
                formal="Close a File",
                usage="close <file_path>",
                description="This command closes a specified file on the server. Provide the file path of the file you wish to close.",
                handler=self.handle_close
            ),
            Command(
                name="read",
                formal="Read a File ",
                usage="read <file_path> <offset>? <length>? [> <local_file>]?",
                description= \
"""This command reads a specified file from the server starting at the given offset and reads the given length of data.
    - <file_path>: The path of the file to read binary data from.
    - <offset>: The starting byte position to begin reading binary data from.
    - <length>: The number of bytes to read in binary format.""",
                handler=self.handle_read
            ),
            Command(
                name="write",
                formal="Write to a File",
                usage="write <file_path> <offset>? [-b]? [< <local_file>]?",
                description= \
"""This command writes content to a specified file on the server. Provide the file path and the content you wish to write.
    - <file_path>: The path of the file to write to on the server.
    - <offset>: The position in the server file to start writing at.
    - <local_file>: The local file from which to read the content. Optionally, use the '-b' flag to indicate binary data.""",
                handler=self.handle_write
            ),
            Command(
                name="delete",
                formal="Delete a File",
                usage="delete <file_path>",
                description="This command deletes a specified file on the server. Provide the file path of the file you wish to delete.",
                handler=self.handle_delete
            ),
            # Command(
            #     name="zk_lock",
            #     formal="Acquire Zookeeper Lock",
            #     usage="Usage: zk_lock <lock_path>",
            #     description="""
            #     This command acquires a lock on a specified path in Zookeeper. Only one client can hold the lock at any given time. 
            #     - <lock_path>: The path in Zookeeper where the lock will be placed.""",
                
            # ),
            # Command(
            #     name="zk_unlock",
            #     formal="Release Zookeeper Lock",
            #     usage="Usage: zk_unlock <lock_path>",
            #     description="""
            #     This command releases the lock on a specified path in Zookeeper. Once released, other clients can acquire the lock.
            #     - <lock_path>: The path in Zookeeper where the lock will be released."""
            # ),
            Command(
                name="help",
                formal="Display Help",
                usage="help",
                description="Displays this help message for all available commands.", 
                handler=self.handle_help
            )
        ]
        
        # Set up command history
        self.setup_history()
    
    def setup_history(self):
        """ Set up the command history using the readline module """
        try:
            readline.read_history_file(HISTORY_FILE)
        except FileNotFoundError:
            pass  # History file might not exist yet

        readline.set_history_length(100)  # Limit the history size to 100 commands
    
    async def websocket_comm(self, uri, data) -> bytes:
        """ Connect to the websocket server and send the command """
        async with websockets.connect(uri) as websocket:
            await websocket.send(data)
            response = await websocket.recv(decode=False)
            # await websocket.close()
            return response

    async def handle_command(self, command):
        """ Handle commands from CLI or shell """
        args = shlex.split(command)

        # Find the command in the available commands list
        matched_command = next((cmd for cmd in self.commands if cmd.name == args[0]), None)

        if matched_command:
            # Call the handler for the matched command
            # await matched_command.handler(*args[1:])
            await matched_command.handler(command)

            # If there is a callback, execute it after the handler
            if matched_command.callback:
                matched_command.callback()
        else:
            print(f"Unknown command: {args[0]}")
    
    '''
    Command handlers
    '''
    async def handle_open(self, command):
        parts = shlex.split(command)
        if not len(parts) == 2:
            print("open takes one argument.")
            return

        parts = parts[1:]
        
        file_path = parts[0]
        
        openRequest = OpenRequest()
        response = await self.websocket_comm(
            nfs_server_uri,
            openRequest.encode(Path(file_path))
        )
        
        openResponse = OpenResponse()
        openResponse.decode(response)
        
        if not openResponse.OK:
            print(colored(openResponse.message, "red"))
            return
        
        if not await self.lock(openResponse.file_node):
            return
        
        print(colored(openResponse.message, "light_blue"))
        
        # Fetch the file first & cached it
        # Future implementation could be to fetch it in the BG (non-blocking)
        readRequest = ReadRequest()
        response = await self.websocket_comm(
            nfs_server_uri,
            readRequest.encode(
                file_node=self.current_file_node
            )
        )
        
        readResponse = ReadResponse()
        readResponse.decode(response)
        
        file_node: FileNode = readResponse.file_node
        file_data: bytes = readResponse.data
        file_id: str = file_node.file_id
        
        temp_file_path = os.path.join(self.temp_folder, file_id)
        self.temp_file = Path(temp_file_path)
        bytes_written: int = -1
        with open(self.temp_file, "wb") as file:
            bytes_written = file.write(file_data)
        
        print(colored(file_node, "yellow"))
        
        assert bytes_written == file_node.size
    
    async def handle_close(self, command):
        parts = shlex.split(command)
        if len(parts) > 1:
            print("close does not take any arguments.")
            return
        
        temp_file_node = self.current_file_node
        # Check if a file opened
        if not await self.unlock():
            return
        
        temp_file_size:int = os.path.getsize(self.temp_file)
        assert temp_file_node.size == temp_file_size
        data: bytes = None
        
        with open(self.temp_file, "rb") as file:
            data = file.read()
        
        # Write file to NFS server
        writeRequest = WriteRequest()
        response = await self.websocket_comm(
            nfs_server_uri,
            writeRequest.encode(
                temp_file_node,
                data=data
            )
        )
        
        writeResponse = WriteResponse()
        writeResponse.decode(response)
        
        if not writeResponse.OK:
            print(colored(writeResponse.message, "red"))
            return
        
        print(colored(writeResponse.message, "light_blue"))
        
        # Continue with closing the file...
        closeRequest = CloseRequest()
        response = await self.websocket_comm(
            nfs_server_uri,
            closeRequest.encode(
                temp_file_node
            )
        )
        
        closeResponse = CloseResponse()
        closeResponse.decode(response)
        
        if not closeResponse.OK:
            print(colored(closeResponse.message, "red"))
            return
        
        os.remove(self.temp_file)
        self.temp_file = None
        
        print(colored(closeResponse.message, "light_blue"))
        print(colored(closeResponse.file_node, "yellow"))
    
    async def handle_write(self, command):
        if not self.has_file_open():
            print("No File open.")
            return
        
        binary_mode: bool = False
        file_path: str = ""
        local_file: str = ""
        offset: int = 0
        
        content = None
        
        # Check if there is a file redirection (<)
        if "<" in command:
            # Split the command at the redirection operator
            command_parts = command.split("<")
            
            # The main write command and the local file to redirect from
            file_command = shlex.split(command_parts[0].strip())    # Main write command
            local_file = command_parts[1].strip()                   # The file to redirect from

            # Check for the -b flag for binary data
            if '-b' in file_command:
                binary_mode = True
                file_command.remove('-b')  # Remove the -b flag from the command
            
            # Extract the file path and offset
            if len(file_command) > 1:
                offset = int(file_command[1])

            try:
                # Read content from the local file
                if binary_mode:
                    with open(local_file, 'rb') as f:
                        content = f.read()  # Read as binary data
                else:
                    with open(local_file, 'r') as f:
                        content = f.read()  # Read as text content
            except Exception as e:
                print(f"Error reading file: {e}")
        else:
            # Without any redirection
            # write <offset> [-b] <string_data>
            file_command = shlex.split(command)[1:]
            
            if '-b' in file_command:
                binary_mode = True
                file_command.remove('-b')  # Remove the -b flag from the command

            file_path = file_command[0]
            
            if len(file_command) > 1:
                offset = int(file_command[0])
                content = file_command[1]
            else:
                content = file_command[0]

        if binary_mode:
            print(f"\tBinary content to write to {file_path} at offset {offset}:")
            print(f"\tSize: {len(content)} bytes")
            print(f"\tMode: Binary")

            # Limit the content display to 10 bytes if it is longer
            if len(content) > 10:
                content_display = content[:10] + b"..."  # Truncate and add ellipsis for bytes
            else:
                content_display = content
            print(f"\tContent (first 10 bytes or full): {content_display.hex()}")
        else:
            print(f"\tText content to write to {file_path} at offset {offset}:")
            print(f"\tLength: {len(content)} characters")
            print(f"\tMode: Character/Text")

            # Limit the content display to 10 characters if it is longer
            if len(content) > 10:
                content_display = content[:10] + "..."  # Truncate and add ellipsis for text
            else:
                content_display = content
            print(f"\tContent (first 10 bytes or full): {content_display}")
        
        bytes_written: int = 0
        if binary_mode:
            with open(self.temp_file, "ab") as file:
                bytes_written = file.write(content)
        else:
            with open(self.temp_file, "a") as file:
                bytes_written = file.write(content)
        self.current_file_node.size += bytes_written
        
    async def handle_read(self, command):
        if not self.has_file_open():
            print("No File open.")
            return

        # Read the entire cached file into memory
        with open(self.temp_file, "rb") as file:
            data: bytes = file.read()

        # 1. Raw bytes
        print(colored("Raw:", "cyan"))
        print(data)
        print()

        # 2. Binary representation
        # Join each byte formatted as an 8-bit binary string, separated by spaces
        binary_repr = " ".join(f"{b:08b}" for b in data)
        print(colored("Binary:", "cyan"))
        print(binary_repr)
        print()

        # 3. Hex representation
        # data.hex() returns a continuous hex string; split into byte-pairs for readability
        hex_pairs = " ".join(data.hex()[i:i+2] for i in range(0, len(data.hex()), 2))
        print(colored("HEX:", "cyan"))
        print(hex_pairs)
        print()

        # 4. UTF-8 interpreted text
        try:
            text = data.decode("utf-8")
            print(colored("UTF-8:", "cyan"))
            print(text)
        except UnicodeDecodeError:
            # Replace undecodable bytes with the Unicode replacement character
            text = data.decode("utf-8", errors="replace")
            print(colored("UTF-8 (with errors replaced):", "cyan"))
            print(text)
    
    async def handle_delete(self, command):
        '''
        TODO: To be implemented...
        '''
        pass
    
    async def handle_help(self, command):
        """ Prints how to use the CLI """
        print("NFS Client CLI Usage:")
        for command in self.commands:
            print(command.get_help_msg())
    
    def has_file_open(self) -> bool:
        return not (self.current_file_node == None or self.current_zk_lock == None or self.temp_file == None)
    
    async def lock(self, file_node: FileNode) -> bool:
        # Check if a file is already opened
        if (not self.current_file_node == None) and (not self.current_zk_lock == None):
            print("A File a already opened! Please close it first.")
            return False
        elif (not self.current_file_node == None) or (not self.current_zk_lock == None):
            print("A File was opened? Current tracker got corrupted, resetting...")
            self.current_file_node = None
            self.current_zk_lock = None
        
        try:  
            self.current_file_node = file_node
            await self.zk_lock(self.current_file_node.file_path.as_posix())
            assert not self.current_file_node == None and not self.current_zk_lock == None
        except AssertionError as e:
            print(f"An error occured while locking file: {e}")
            return False

        return True

    async def unlock(self) -> bool:
        if not self.has_file_open():
            print("No File open.")
            self.current_file_node = None
            self.current_zk_lock = None
            return False
        
        try:  
            self.current_file_node = None
            await self.zk_unlock()
        except AssertionError as e:
            print(f"An error occured while unlocking file: {e}")
            return False

        return True

    async def zk_lock(self, lock_path):
        """ Acquire lock in Zookeeper """
        lock = self.zk.Lock(lock_path, "client_lock")
        print("Attempting to acquire lock...")
        lock.acquire()
        assert lock.is_acquired == True
        self.current_zk_lock = lock
        print(f"Lock acquired at {lock_path}")

    async def zk_unlock(self):
        """ Release lock in Zookeeper """
        if self.current_zk_lock == None:
            return True
        # lock = self.zk.Lock(lock_path, "client_lock")
        lock = self.current_zk_lock
        lock_path = lock.path
        print("Attempting to release lock...")
        lock.release()
        assert lock.is_acquired == False
        self.current_zk_lock = None
        print(f"Lock released at {lock_path}")

    def start_cli(self):
        """ Start the interactive CLI for the client """
        print("NFS Client CLI by JUN WEI WANG (22302016002). Type 'help' for available commands.")
        while True:
            try:
                bang = colored("nfs> ", "green")
                command = input(bang)
                if command.strip().lower() == 'exit':
                    break

                # Save the command to history
                readline.add_history(command)
                asyncio.run(self.handle_command(command))

            except Exception as e:
                print(f"Error: {e}")
                continue

        # Save history when exiting
        readline.write_history_file(HISTORY_FILE)

def parse_args():
    parser = argparse.ArgumentParser(description="NFS Client (WebSocket) CLI by JUN WEI WANG (22302016002)")
    parser.add_argument('--host', type=str, default=NFS_SERVER, help="Host IP address of the NFS server")
    parser.add_argument('--port', type=int, default=NFS_PORT, help="Port number for the WebSocket server")
    parser.add_argument('--binary-port', type=int, default=NFS_FS_PORT, help="Port number for the binary WebSocket server")
    parser.add_argument('--zk-host', type=str, default=ZK_HOST, help="Zookeeper server host")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    client = NFSClient(args.host, args.port, args.binary_port, args.zk_host)
    client.start_cli()
