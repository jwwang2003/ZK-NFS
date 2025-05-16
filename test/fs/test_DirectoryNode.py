import unittest
from pathlib import Path
from nfs.fs import DirectoryNode, FileNode  # Assuming these classes are in file_system.py

class TestDirectoryNode(unittest.TestCase):
    def setUp(self):
        """Set up a DirectoryNode instance for testing."""
        self.root_dir = DirectoryNode("root")

    def test_create_directory(self):
        """Test creating a new directory."""
        new_dir = self.root_dir.create_directory("subdir")
        self.assertTrue("subdir" in self.root_dir.children)
        self.assertIsInstance(new_dir, DirectoryNode)

    def test_create_directory_existing(self):
        """Test creating a directory that already exists."""
        self.root_dir.create_directory("subdir")
        with self.assertRaises(FileExistsError):
            self.root_dir.create_directory("subdir")

    def test_create_file(self):
        """Test creating a new file."""
        new_file = self.root_dir.create_file("file1.txt", "content")
        self.assertTrue("file1.txt" in self.root_dir.children)
        self.assertIsInstance(new_file, FileNode)

    def test_create_file_existing(self):
        """Test creating a file that already exists."""
        self.root_dir.create_file("file1.txt", "content")
        with self.assertRaises(FileExistsError):
            self.root_dir.create_file("file1.txt", "new content")

    def test_delete_directory(self):
        """Test deleting a directory."""
        self.root_dir.create_directory("subdir")
        self.root_dir.delete_directory("subdir")
        self.assertNotIn("subdir", self.root_dir.children)

    def test_delete_directory_not_found(self):
        """Test deleting a directory that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.root_dir.delete_directory("nonexistent_dir")

    def test_delete_file(self):
        """Test deleting a file."""
        self.root_dir.create_file("file1.txt", "content")
        self.root_dir.delete_file("file1.txt")
        self.assertNotIn("file1.txt", self.root_dir.children)

    def test_delete_file_not_found(self):
        """Test deleting a file that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.root_dir.delete_file("nonexistent_file.txt")

    def test_rename_directory(self):
        """Test renaming a directory."""
        subdir = self.root_dir.create_directory("subdir")
        subdir.create_file("test.txt", Path("root/subdir/test.txt"))
        subdir.create_file("file1.txt", Path("root/subdir/file1.txt"))
        self.root_dir.rename_directory("subdir", "new_subdir")
        self.assertTrue("new_subdir" in self.root_dir.children)
        self.assertFalse("subdir" in self.root_dir.children)

    def test_rename_directory_not_found(self):
        """Test renaming a directory that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.root_dir.rename_directory("nonexistent_dir", "new_name")

    def test_rename_file(self):
        """Test renaming a file."""
        fileNode = self.root_dir.create_file("file1.txt", Path(self.root_dir.name, "file1.txt"))
        self.assertTrue("file1.txt" == fileNode.name)

        fileNode = self.root_dir.rename_file("file1.txt", "file2.txt")
        self.assertTrue("file2.txt" == fileNode.name)

    def test_rename_file_not_found(self):
        """Test renaming a file that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.root_dir.rename_file("nonexistent_file.txt", "new_name")

    def test_get_file(self):
        """Test getting a file by absolute path."""
        self.root_dir.create_file("file1.txt", "content")
        file = self.root_dir.get_file(["file1.txt"])
        self.assertEqual(file.name, "file1.txt")

    def test_get_file_not_found(self):
        """Test getting a file that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.root_dir.get_file(["nonexistent_file.txt"])

    def test_list_files(self):
        """Test listing files and directories."""
        self.root_dir.create_file("file1.txt", "content")
        self.root_dir.create_directory("subdir")
        files = self.root_dir.list()
        self.assertIn("file1.txt", files)
        self.assertIn("subdir", files)

    def tearDown(self):
        """Clean up any remaining test artifacts."""
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
