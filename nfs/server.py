import argparse
import asyncio
import websockets
import json
import os
import sys
import signal

from nfs.constants import NFS_SERVER, NFS_PORT, NFS_FS_PORT, PERSIST_DIR
from nfs.fs import FileSystem, FileNode
from nfs.packet import OpenRequest, OpenResponse, \
    CloseRequest, CloseResponse, \
    ReadRequest, ReadResponse, \
    WriteRequest, WriteResponse

# NFS Server that handles file operations using WebSocket
class NFSServer:
    def __init__(self, host: str, port: int, fs_port: int, base_data_folder: str):
        self.host = host
        self.port = port
        self.fs_port = fs_port
        
        self.fs = FileSystem(base_data_folder=base_data_folder)
        if os.path.exists(PERSIST_DIR):
            self.fs.load(PERSIST_DIR)
        
        # Catching SIGINT (Ctrl+C) to save state before exiting
        signal.signal(signal.SIGINT, self.handle_exit)
    
    async def start(self):
        # Start both servers
        text_server = await websockets.serve(self.handle_nfs, self.host, self.port)
        binary_server = await websockets.serve(self.handle_file, self.host, self.fs_port)

        print(f"WebSocket server running on ws://{self.host}:{self.port} for NFS commands.")
        print(f"WebSocket server running on ws://{self.host}:{self.fs_port} for file transfers.")

        await text_server.wait_closed()
        await binary_server.wait_closed()
    
    def handle_exit(self, signum, frame):
        """Gracefully handle shutdown and save the FileSystem state."""
        print("Server shutting down... Saving file system state.")
        self.fs.save(PERSIST_DIR)
        sys.exit(0)
    
    async def save_fs_periodically(self):
        """Periodically save the file system every second."""
        while True:
            await asyncio.sleep(1)  # Wait for 1 second
            try:
                # print("Saving file system state...")
                self.fs.save(PERSIST_DIR)
            except Exception as e:
                print(f"Error during periodic save: {e}")

    async def handle_nfs(self, websocket: websockets.ServerConnection):
        # await websocket.send("Connected to NFS server.\nType 'help' for available commands.\n")

        while True:
            try:
                data = await websocket.recv(decode=False)
                if not data:
                    break
                
                command = json.loads(bytes.decode(data, "utf-8"))  # Expecting a JSON command
                action = command.get("action", "").lower()
                
                if action == "open":
                    # Decode request
                    openRequest = OpenRequest()
                    openRequest.decode(data)
                    
                    file_path = openRequest.file_path
                    
                    file_node: FileNode = None
                    
                    # Set-up the response
                    openResponse = OpenResponse()
                    try:
                        file_node = self.fs.open(file_path)
                    except Exception as e:
                        await websocket.send(
                            openResponse.encode(
                                msg=f"{e}",
                                OK=False
                            )
                        )
                    
                    await websocket.send(
                        openResponse.encode(
                            msg=f"File {file_path} opened successfully.",
                            OK=True,
                            file_node=file_node
                        )
                    )
                    # END
                elif action == "close":
                    closeRequest = CloseRequest()
                    closeRequest.decode(data)
                    
                    file_path = closeRequest.file_node.file_path
                    file_node: FileNode = None
                    
                    closeResponse = CloseResponse()
                    try:
                        file_node = self.fs.mutate(file_path, closeRequest.file_node)
                    except Exception as e:
                        await websocket.send(
                            closeResponse.encode(
                                msg=f"{e}.",
                                OK=False
                            )
                        )
                    
                    await websocket.send(
                        closeResponse.encode(
                            msg=f"File {file_path} closed successfully.",
                            OK=True,
                            file_node=file_node
                        )
                    )
                    # END
                elif action == "read":
                    # The client wants to download a file FROM the server
                    readRequest = ReadRequest()
                    readRequest.decode(data)
                    
                    file_node: FileNode = readRequest.file_node
                    file_path = file_node.file_path
                    
                    readResponse = ReadResponse()
                    data: bytes = None
                    
                    try:
                        data = self.fs.get_file(file_path)
                    except Exception as e:
                        await websocket.send(
                            readResponse.encode(
                                msg=f"{e}.",
                                OK=False
                            )
                        )
                        break
                    
                    readResponse.file_node = file_node
                    readResponse.data = data
                    await websocket.send(
                        readResponse.encode(
                            msg=f"Read data from File {file_path}",
                            OK=True,
                            data=readResponse.data
                        )
                    )
                    # END
                elif action == "write":
                    writeRequest = WriteRequest()
                    writeRequest.decode(data)
                    
                    file_node: FileNode = writeRequest.file_node
                    data: bytes = writeRequest.data
                    
                    file_path = file_node.file_path

                    writeResponse = WriteResponse()
                    bytes_written: int = 0
                    
                    try:
                        bytes_written = self.fs.save_file(file_path, data)
                    except Exception as e:
                        await websocket.send(
                            writeResponse.encode(
                                msg=f"{e}.",
                                OK=False
                            )
                        )
                        break
                    
                    assert bytes_written == file_node.size
                    
                    await websocket.send(
                        writeResponse.encode(
                            msg=f"Wrote data to File {file_path}.",
                            OK=True,
                            file_node=file_node,
                            bytes_written=bytes_written
                        )
                    )
                else:
                    await websocket.send("Unknown command.\nType 'help' for available commands.")
            except websockets.exceptions.ConnectionClosedOK as e:
                # print(f"Connection was closed gracefully: {e}")
                break
            except Exception as e:
                await websocket.send(f"Error: {str(e)}")
                break

    async def handle_file(self, websocket):
        await websocket.send("Connected to Binary File Transfer server.")

        while True:
            try:
                data = await websocket.recv(decode=False)
                if not data:
                    break
                
                command = json.loads(bytes.decode(data, "utf-8"))  # Expecting a JSON command
                action = command.get("action", "").lower()
                
                '''
                Supported actions:
                - read
                - write (over-writes)
                '''
                
                if action == 'read':
                    # The client wants to download a file FROM the server
                    
                    closeRequest = CloseRequest()
                    closeRequest.decode(data)
                    
                    file_path = closeRequest.file_node.file_path
                    file_node: FileNode = None
                    
                    closeResponse = CloseResponse()
                    
                    
                    file_bytes: bytes = self.fs.get_file()
                    
                    pass
                elif action == 'write':
                    # The client wants to upload a file TO the server
                    
                    pass
                else:
                    await websocket.send({ "message": "Unknown file command.\n", "OK": False })
            except websockets.exceptions.ConnectionClosedOK as e:
                # print(f"Connection was closed gracefully: {e}")
                break
            except Exception as e:
                await websocket.send(f"Error: {str(e)}")
                break


# Command-line argument parsing
def parse_args():
    parser = argparse.ArgumentParser(description="WebSocket NFS Server (by JUN WEI WANG 22302016002)")
    
    # Server Configuration Options
    parser.add_argument('--host', type=str, default=NFS_SERVER, help="Host IP address (default: 127.0.0.1)")
    parser.add_argument('--port', type=int, default=NFS_PORT, help="Port number for the server (default: 8080)")
    parser.add_argument('--binary-port', type=int, default=NFS_FS_PORT, help="Port number for binary file transfer server (default: 8081)")
    parser.add_argument('--base-dir', type=str, default='storage', help="Base directory for storing files (default: 'storage')")
    
    return parser.parse_args()

# Main function to run the server
if __name__ == "__main__":
    args = parse_args()

    server = NFSServer(
        host=args.host, 
        port=args.port, 
        fs_port=args.binary_port, 
        base_data_folder=args.base_dir
    )

    # Start the WebSocket server
    asyncio.get_event_loop().run_until_complete(server.start())
    asyncio.get_event_loop().run_until_complete(server.save_fs_periodically())
