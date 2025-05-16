import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch, mock_open
from nfs.fs import FileNode

class TestFileNode(unittest.TestCase):
    @patch('time.time', return_value=1000000)  # Mock time to avoid testing on real time
    def setUp(self, mock_time):
        """Set up the test environment for FileNode."""
        # Set up a FileNode instance for testing
        self.file_node = FileNode(name="test.txt", file_path=Path("/path/to/file"))
    
    def test_generate_file_id(self):
        """Test the generation of the file ID based on name and content."""
        expected_file_id = hashlib.sha256("test.txt/path/to/file".encode()).hexdigest()
        self.assertEqual(self.file_node.file_id, expected_file_id)
    
    def test_rename(self):
        """Test renaming a file and updating its file ID and modified time."""
        new_name = "new_test.txt"
        old_file_id = self.file_node.file_id  # Store old file_id to compare after renaming
        
        with patch('time.time', return_value=2000000):  # Mock the time to ensure the timestamp is updated
            self.file_node.rename(new_name)
        
        self.assertEqual(self.file_node.name, new_name)  # Check if the name was updated
        self.assertNotEqual(self.file_node.file_id, old_file_id)  # Check if file ID was updated
        self.assertEqual(self.file_node.modified_at, 2000000)  # Check if modified_at was updated correctly
    
    # @patch('builtins.open', new_callable=mock_open)  # Mock open to prevent actual file operations
    # def test_modify(self, mock_file):
    #     """Test modifying the content of the file and updating the modification timestamp."""
    #     new_content = "new file content"
        
    #     with patch('time.time', return_value=3000000):  # Mock time to ensure the timestamp is updated
    #         self.file_node.modify(new_content)
        
    #     self.assertEqual(self.file_node.content, new_content)  # Check if content was updated
    #     self.assertEqual(self.file_node.modified_at, 3000000)  # Check if modified_at was updated correctly
    #     mock_file.assert_called_with(self.file_node.file_path, 'w')  # Ensure file was written with new content
    
    def test_repr(self):
        """Test the string representation of the FileNode."""
        expected_repr = f"FileNode(name={self.file_node.name}, file_id={self.file_node.file_id}, file_path={self.file_node.file_path}, created_at=1000000, modified_at=1000000)"
        self.assertEqual(repr(self.file_node), expected_repr)

if __name__ == '__main__':
    unittest.main(verbosity=2)
