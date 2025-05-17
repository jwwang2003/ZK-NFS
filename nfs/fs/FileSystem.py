#!/usr/bin/env python

'''
This module is the FileSystem class.
This module defines the FileNode class for simulating a basic file in a virtual file system.
It provides functionality to create, rename, modify, and manage files, as well as generate unique identifiers for them.

The FileNode represents a file with associated content, file path, and metadata, such as creation and modification timestamps.
Note that the file content is stored in memory (or could be saved to disk if extended) and managed through the `file_path`.

Main features include:
- Creating and managing files using nodes.
- Renaming files and updating their metadata.
- Modifying file content and updating the modification timestamp.
- Generating unique file IDs using file name and content.
- Retrieving the file path and metadata (timestamps).
'''

__author__          = "JUN WEI WANG"
__copyright__       = "Copyright 2025"
__credits__         = ["JUN WEI WANG"]
__license__         = "GPL"
__version__         = "1.0.0"
__maintainer__      = "JUN WEI WANG"
__email__           = "wjw_03@outlook.com"

import threading
import os
import time
import json
from pathlib import Path
from typing import List, Dict

from .FileNode import FileNode
from .DirectoryNode import DirectoryNode

class FileSystem:
    def __init__(self, root_name: str = "/", base_data_folder: str = "storage"):
        """
        Initializes the virtual file system with the specified root directory and a locking mechanism to handle race conditions.
        """
        self.base_data_folder = base_data_folder
        self.root = DirectoryNode(root_name)
        os.makedirs(base_data_folder, exist_ok=True)
        self.lock = threading.Lock()  # Thread lock initialization

    '''
    Base methods
    '''
    
    def open(self, file_path: str, file_node: FileNode = None) -> FileNode:
        '''
        - Returns the FileNode at the specified path
        - Automatically creates folders recursively
        - If file_node is not None, update the file found with the data
        '''
        parts = self._validate_and_split_path(file_path)
        current_dir = self.root
        t_path = ""
        for part in parts[1:-1]:
            try:
                t_path += f"/{part}"
                with self.lock:
                    current_dir = self._traverse_directory(current_dir, part)
            except FileNotFoundError as e:
                # Directory DNE, then create one
                current_dir = self.create_directory(Path(t_path).as_posix())
        # Check if file exists
        file_to_open: FileNode = None
        with self.lock:
            file_to_open = current_dir.children.get(parts[-1])
        
        # If the file doesn't exist, create the folders and the file
        if not file_to_open:
            # Create a new file node
            file_to_open = self.create_file(file_path)
        
        if file_to_open and file_node:
            file_to_open = file_node
            with self.lock:
                current_dir.mutate_file(parts[-1], file_to_open)
        
        return file_to_open

    def delete(self, file: str) -> FileNode:
        if isinstance(file, FileNode):
            t: FileNode = file
            file = t.file_path
        
        parts = self._validate_and_split_path(file)
        current_dir = self.root
        
        with self.lock:
            for part in parts[1:-1]:
                try:
                    current_dir = self._traverse_directory(current_dir, part)
                except FileNotFoundError as e:
                    raise e

        # Attempt to find the file to delete
        file_to_delete= current_dir.children.get(parts[-1])

        if not file_to_delete or not isinstance(file_to_delete, FileNode):
            raise FileNotFoundError(f"File {file} not found")

        # Ensure the file exists before deletion
        file_path_to_delete = Path(self.base_data_folder, file_to_delete.file_id)
        if file_path_to_delete.exists():
            os.remove(file_path_to_delete)  # Delete the file from the disk
        
        with self.lock:
            # Finally, delete the file from the tree
            return current_dir.delete_file(parts[-1])
    
    def mutate(self, file: str, new_file_node: FileNode) -> FileNode:
        """
        Mutates the contents of an existing file and updates its modification timestamp.
        """
        if isinstance(file, FileNode):
            t: FileNode = file
            file = t.file_path
        
        parts = self._validate_and_split_path(file)
        current_dir = self.root
        
        with self.lock:
            for part in parts[1:-1]:
                try:
                    current_dir = self._traverse_directory(current_dir, part)
                except FileNotFoundError as e:
                    raise e
        
        with self.lock:
            file_to_mutate = current_dir.children.get(parts[-1])
            
            if not file_to_mutate or not isinstance(file_to_mutate, FileNode):
                raise FileNotFoundError(f"File {file} not found")
        
            # file_to_mutate.modified_at = time.time()  # Update the modification time
            new_file_node.modified_at = time.time()
            
            current_dir.mutate_file(parts[-1], new_file_node)
            return new_file_node
    
    '''
    Internal methods (critical sections)
    '''
    
    def create_directory(self, path: str):
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(path)
            current_dir = self.root
            for part in parts[:-1]:
                current_dir = self._traverse_directory(current_dir, part)
            return current_dir.create_directory(parts[-1])

    def create_file(self, path, content: str = "") -> FileNode:
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(path)
            current_dir = self.root
            for part in parts[1:-1]:
                current_dir = self._traverse_directory(current_dir, part)
            
            if not isinstance(path, Path):
                path = Path(path)
            
            # Create the file in the directory
            new_file = current_dir.create_file(parts[-1], path)
            
            # Ensure the file is saved to disk (if required by your file system)
            file_path = Path(self.base_data_folder, new_file.file_id)
            file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
            with open(file_path, 'w') as f:
                new_file.size = f.write(content)

            return new_file

    def delete_directory(self, path: str):
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(path)
            current_dir = self.root

            i = 0
            for part in parts[1:-1]:
                i = i + 1
                current_dir = self._traverse_directory(current_dir, part)

            if i < len(parts[:-1]) - 1:
                raise FileNotFoundError(f"Directory {part} not found in path.")
            
            if not (len(current_dir.children[parts[-1]].children) == 0):
                raise EnvironmentError(f"Directory {path} is not empty.")
            
            current_dir.delete_directory(parts[-1])

    def delete_file(self, path: str):
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(path)

            current_dir = self.root
            for part in parts[:-1]:
                current_dir = self._traverse_directory(current_dir, part)

            # Attempt to delete the file from the file system
            file_to_delete = current_dir.children.get(parts[-1])

            if not file_to_delete or not isinstance(file_to_delete, FileNode):
                raise FileNotFoundError(f"File {path} not found")

            # Ensure the file exists before deletion
            file_path = Path(self.base_data_folder, file_to_delete.file_id)
            if file_path.exists():
                os.remove(file_path)  # Remove the file from the system

            current_dir.delete_file(parts[-1])

    def rename_directory(self, old_path: str, new_name: str):
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(old_path)
            current_dir = self.root
            for part in parts[:-1]:
                current_dir = self._traverse_directory(current_dir, part)
            
            current_dir.rename_directory(parts[-1], new_name)

    def rename_file(self, old_path: str, new_name: str):
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(old_path)
            current_dir = self.root
            for part in parts[:-1]:
                current_dir = self._traverse_directory(current_dir, part)
            
            old_id = current_dir.get_file(parts[1:]).file_id
            file = current_dir.rename_file(parts[-1], new_name)
            
            os.rename(
                Path(self.base_data_folder, old_id),
                Path(self.base_data_folder, file.file_id)
            )

    def get_file_node(self, abs_path: str) -> FileNode:
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(abs_path)
            try:
                file = self.root.get_file(parts)
                return file
            except FileNotFoundError:
                raise FileNotFoundError(f"File {abs_path} not found")
    
    def get_file(self, abs_path: str) -> bytes:
        with self.lock:  # Locking the critical section
            parts = self._validate_and_split_path(abs_path)
            file_node: FileNode = None
            try:
                file_node = self.root.get_file(parts)
            except FileNotFoundError:
                raise FileNotFoundError(f"File {abs_path} not found")
            
            file_path = Path(self.base_data_folder, file_node.file_id)
            
            try:
                with open(file_path, 'rb') as f:
                    return f.read()
            except FileNotFoundError:
                raise FileNotFoundError(f"File {abs_path} not found")
    
    def save_file(self, abs_path: str, data: bytes) -> int:
        with self.lock:
            # Validate the path and locate the FileNode
            parts = self._validate_and_split_path(abs_path)
            try:
                file_node = self.root.get_file(parts)
            except FileNotFoundError:
                raise FileNotFoundError(f"File {abs_path} not found")

            # Compute the on-disk location from the file_id
            file_path = Path(self.base_data_folder) / file_node.file_id

            # Write the data
            try:
                with open(file_path, 'wb') as f:
                    bytes_written = f.write(data)
                    f.flush()
                    return bytes_written
            except IOError as e:
                raise IOError(f"Failed to write to {abs_path}: {e}")
            except Exception as e:
                raise Exception(e)

    def save(self, file_path: str):
        with self.lock:  # Locking the critical section
            with open(file_path, 'w') as f:
                json.dump(self._serialize(self.root), f)

    def load(self, file_path: str):
        with self.lock:  # Locking the critical section
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.root = self._deserialize(data)

    def _serialize(self, node) -> Dict:
        """Serialize the file system into a dictionary format"""
        if isinstance(node, DirectoryNode):
            return {"type": "directory", "name": node.name, "children": {k: self._serialize(v) for k, v in node.children.items()}}
        elif isinstance(node, FileNode):
            return {"type": "file", "name": node.name, "size": node.size, "file_path": node.file_path.as_posix(), "file_id": node.file_id, "created_at": node.created_at, "modified_at": node.modified_at}
        else:
            raise TypeError("Unknown node type")

    def _deserialize(self, data: Dict) -> DirectoryNode:
        """Deserialize the file system from a dictionary format"""
        if data['type'] == 'directory':
            dir_node = DirectoryNode(data['name'])
            for child_name, child_data in data['children'].items():
                dir_node.children[child_name] = self._deserialize(child_data)
            return dir_node
        elif data['type'] == 'file':
            return FileNode(data['name'], Path(data['file_path']))
        else:
            raise TypeError("Unknown node type")
    
    def _validate_and_split_path(self, path: str) -> List[str]:
        p = Path(path)
        if not p.is_absolute():
            raise ValueError(f"Path must be absolute: {path}")
        return [part for part in p.parts if part]

    def _traverse_directory(self, current_dir: DirectoryNode, part: str) -> DirectoryNode:
        """Traverse a directory and return the next directory node"""        
        if current_dir.name == part:
            return current_dir
        elif part in current_dir.children and isinstance(current_dir.children[part], DirectoryNode):
            return current_dir.children[part]
        else:
            raise FileNotFoundError(f"Directory {part} not found in path.")