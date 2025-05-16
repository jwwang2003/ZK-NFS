#!/usr/bin/env python

'''
This module defines the DirectoryNode and FileNode classes for simulating a basic file system structure.
It provides functionality to create, delete, rename, and retrieve files and directories, similar to the operations 
performed in a real file system. The DirectoryNode represents a directory that can contain files or other directories 
as children, while the FileNode represents a file with content and metadata.

Note that the actual file data is not saved in this data structure, it is saved on the host OS based on the file ID.

Main features include:
- Creating and managing directories and files using nodes.
- Deleting file and directory nodes.
- Renaming file and directory nodes.
- Retrieving file nodes based on absolute paths.
- Listing contents (files/dirs) of directories.
'''

__author__          = "JUN WEI WANG"
__copyright__       = "Copyright 2025"
__credits__         = ["JUN WEI WANG"]
__license__         = "GPL"
__version__         = "1.0.0"
__maintainer__      = "JUN WEI WANG"
__email__           = "wjw_03@outlook.com"

import time
from pathlib import Path
from typing import List, Dict

from .FileNode import FileNode

class DirectoryNode:
    def __init__(self, name: str):
        """
        Initializes a new directory node with the specified name and an empty dictionary of child nodes (which can be files or directories).
        """
        self.name = name            # Name of the directory
        self.children: Dict[str, 'DirectoryNode' | FileNode] = {}

    def create_directory(self, name: str) -> 'DirectoryNode':
        """
        Creates a new subdirectory with the given name if it doesn't already exist, and adds it to the current directory's children. If the directory exists, raises a FileExistsError.
        """
        if name not in self.children:
            new_dir = DirectoryNode(name)
            self.children[name] = new_dir
            return new_dir
        raise FileExistsError(f"Directory {name} already exists")

    def create_file(self, name: str, file_path: Path) -> FileNode:
        """
        Creates a new file with the given name and optional content. It writes the content to disk and adds the file to the directory's children. If the file already exists, raises a FileExistsError.
        """
        if name not in self.children:
            new_file = FileNode(name, file_path)
            file_path = Path(new_file.file_path)
            self.children[name] = new_file
            return new_file
        raise FileExistsError(f"File {name} already exists")

    def mutate_file(self, name: str, file_node: FileNode) -> FileNode:
        """
        Mutates the FileNode by modifying its name, content, or both.
        """
        if not name or not file_node:
            raise FileNotFoundError(f"File mutation has undefiend properties.")
        
        if name not in self.children:
            raise FileNotFoundError(f"File {name} does not exist in directory.")
        
        file_node.modified_at = time.time()
        self.children[name] = file_node
        return file_node
        
    
    def delete_directory(self, name: str, recursive = False) -> List[str]:
        """
        Deletes the subdirectory with the given name from the current directory if it exists. If the directory doesn't exist, raises a FileNotFoundError.
        """ 
        if name in self.children and isinstance(self.children[name], DirectoryNode):
            node = self.children[name]
            if len(node.children) == 0:
                deleted_directory_node = self.children[name]
                del self.children[name]
                return []
            if not len(node.children) == 0 and recursive:
                ids: List[str] = self._collect_file_ids(node)
                return ids
            else:
                raise EnvironmentError("Directory is not empty.")
        else:
            raise FileNotFoundError(f"Directory {name} not found")
        
    def _collect_file_ids(self, node: 'DirectoryNode') -> List[str]:
        """
        Recursively collect file_ids from all FileNodes in this directory and its subdirectories.
        """
        file_ids = []
        for child in node.children.values():
            if isinstance(child, FileNode):
                file_ids.append(child.file_id)
            elif isinstance(child, DirectoryNode):
                # Recurse into subdirectories
                file_ids.extend(self._collect_file_ids(child))
        return file_ids

    def delete_file(self, name: str) -> FileNode:
        """
        Deletes the file with the given name from the current directory and removes it from disk. If the file doesn't exist, raises a FileNotFoundError.
        """
        if name in self.children and isinstance(self.children[name], FileNode):
            deleted_node = self.children[name]
            del self.children[name]
            return deleted_node
        else:
            raise FileNotFoundError(f"File {name} not found")

    def rename_directory(self, old_name: str, new_name: str) -> List[ list[int, int] ]:
        """
        Renames the subdirectory with the given old name to the new name if it exists. If the directory doesn't exist, raises a FileNotFoundError.
        """
        if old_name in self.children and isinstance(self.children[old_name], DirectoryNode):
            self.children[old_name].name = new_name
            self.children[new_name] = self.children.pop(old_name)
            return self._rename_directory_helper(new_name, self.children[new_name])
        else:
            raise FileNotFoundError(f"Directory {old_name} not found")
    
    def _rename_directory_helper(self, new_name, node: 'DirectoryNode', depth = 0) -> List[ list[int, int] ]:
        ids: List[ list[int, int] ] = []
        for child in node.children.values():
            if isinstance(child, FileNode):
                path = child.file_path  # /.../old_dir_name/file.ext
                parts = list(path.parts)
                parts[-(2 + depth)] = new_name
                child.file_path = Path(*parts)
                old_id = child.file_id
                new_id = child.generate_file_id()
                ids.append([old_id, new_id])
            elif isinstance(child, DirectoryNode):
                # Recurse into subdirectories
                ids.extend(self._collect_file_ids(new_name, child, depth + 1))
        return ids

    def rename_file(self, old_name: str, new_name: str) -> FileNode:
        """
        Renames the file with the given old name to the new name, both in memory and on disk. If the file doesn't exist, raises a FileNotFoundError.
        """
        if old_name in self.children and isinstance(self.children[old_name], FileNode):
            self.children[old_name].rename(new_name)
            self.children[new_name] = self.children[old_name]
            del self.children[old_name]
            # NOTE: File id changes
            return self.children[new_name]
        else:
            raise FileNotFoundError(f"File {old_name} not found")

    def get_file(self, path: List[str]) -> FileNode:
        """
        Retrieves the file at the specified path (relative to current self).
        Traverses the directories in the path and returns the file node if found, otherwise raises a FileNotFoundError.
        """
        current_dir: DirectoryNode = self
        # [1:-1], because this is a abs path, ignore the root "/"
        for i, part in enumerate(path[1:]):
            t = current_dir.children.get(part)
            if t and (isinstance(current_dir.children[part], FileNode)):
                break
            if part in current_dir.children.keys():
                current_dir = current_dir.children[part]
            else:
                raise FileNotFoundError(f"Directory {part} not found in path.")
        
        file_name = path[-1]
        if file_name in current_dir.children and isinstance(current_dir.children[file_name], FileNode):
            return current_dir.children[file_name]
        else:
            raise FileNotFoundError(f"File {file_name} not found in path.")

    def list(self) -> List:
        """
        Returns a list of names of all files and directories directly contained within the current directory.
        """
        return [child.name for child in self.children.values()]