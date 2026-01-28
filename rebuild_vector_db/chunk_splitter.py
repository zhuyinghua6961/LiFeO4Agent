"""
ChunkSplitter module for splitting cleaned Markdown into fixed-size chunks.
"""

import re
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class ChunkData:
    """Data structure for a text chunk."""
    chunk_id: str              # Unique ID: {source}_{chunk_index}
    text: str                  # Chunk text content
    source: str                # Document identifier
    chunk_index: int           # Chunk index (starting from 0)
    start_index: int           # Start position in original text
    end_index: int             # End position in original text
    section: str               # Section name
    text_type: str             # Text type (text/table_caption)
    doi: Optional[str]         # DOI (if available)
    metadata: Dict[str, Any]   # Other metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'source': self.source,
            'chunk_index': self.chunk_index,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'section': self.section,
            'text_type': self.text_type,
            'doi': self.doi,
            'metadata': self.metadata
        }


class ChunkSplitter:
    """Splits cleaned Markdown text into fixed-size chunks."""
    
    def __init__(self, chunk_size: int = 550, chunk_overlap: int = 100, doi_mapping_file: str = None, filter_references: bool = True):
        """
        Initialize the chunk splitter.
        
        Args:
            chunk_size: Target size for each chunk (default: 550)
            chunk_overlap: Overlap between consecutive chunks (default: 100)
            doi_mapping_file: Path to DOI mapping JSON file
            filter_references: Whether to filter out REFERENCES section (default: True)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.doi_mapping_file = doi_mapping_file
        self.filter_references = filter_references
        
        # Load DOI mapping if provided
        self.doi_mapping = {}
        if doi_mapping_file:
            try:
                with open(doi_mapping_file, 'r', encoding='utf-8') as f:
                    self.doi_mapping = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load DOI mapping file: {e}")
        
        # Initialize LangChain text splitter with specified separators
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def split(self, text: str, source: str) -> List[ChunkData]:
        """
        Split text into chunks.
        Filters out REFERENCES section if filter_references is True.
        
        Args:
            text: Cleaned Markdown text
            source: Document identifier (filename)
            
        Returns:
            List[ChunkData]: List of chunks
        """
        # Filter out REFERENCES section if enabled
        if self.filter_references:
            text = self._filter_references_section(text)
        
        # Use LangChain to split text
        chunk_texts = self.text_splitter.split_text(text)
        
        chunks = []
        current_position = 0
        
        for chunk_index, chunk_text in enumerate(chunk_texts):
            # Calculate position information
            start_index, end_index = self._calculate_position(text, chunk_text, current_position)
            
            # Extract metadata
            metadata = self.extract_metadata(chunk_text, start_index, text, source)
            
            # Create ChunkData object
            chunk_data = ChunkData(
                chunk_id=f"{source}_{chunk_index}",
                text=chunk_text,
                source=source,
                chunk_index=chunk_index,
                start_index=start_index,
                end_index=end_index,
                section=metadata.get('section', 'Unknown'),
                text_type=metadata.get('text_type', 'text'),
                doi=metadata.get('doi'),
                metadata=metadata
            )
            
            chunks.append(chunk_data)
            
            # Update position for next chunk (accounting for overlap)
            current_position = start_index + 1
        
        return chunks
    
    def _filter_references_section(self, text: str) -> str:
        """
        Filter out REFERENCES section from text.
        
        Args:
            text: Input text
            
        Returns:
            str: Text with REFERENCES section removed
        """
        # Find REFERENCES section header
        references_patterns = [
            r'\n##\s*\d*\.?\s*REFERENCES?\s*\n',
            r'\n####\s*\d*\.?\s*REFERENCES?\s*\n',
            r'\n##\s*\d*\.?\s*BIBLIOGRAPHY\s*\n',
            r'\n####\s*\d*\.?\s*BIBLIOGRAPHY\s*\n',
        ]
        
        for pattern in references_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return text up to the REFERENCES section
                return text[:match.start()]
        
        # If no REFERENCES section found, return original text
        return text
    
    def extract_metadata(self, chunk: str, position: int, full_text: str = None, source: str = None) -> Dict[str, Any]:
        """
        Extract metadata from a chunk.
        
        Args:
            chunk: Chunk text
            position: Position in original text
            full_text: Full text for context (optional)
            source: Source filename (optional)
            
        Returns:
            Dict[str, Any]: Extracted metadata
        """
        metadata = {}
        
        # Extract section using regex
        section = self._extract_section(chunk, full_text, position)
        metadata['section'] = section
        
        # Determine text_type based on keywords
        text_type = self._determine_text_type(chunk)
        metadata['text_type'] = text_type
        
        # Extract DOI from filename or content
        doi = self._extract_doi(source, chunk)
        metadata['doi'] = doi
        
        return metadata
    
    def _extract_section(self, chunk: str, full_text: str = None, position: int = 0) -> str:
        """
        Extract section name from chunk or surrounding context.
        
        Looks for patterns like:
        - ## 1. Introduction
        - ## 2. Methods
        - ## 3. Results
        - ## 4. Discussion
        - ## 5. Conclusion
        
        Args:
            chunk: Chunk text
            full_text: Full text for context
            position: Position in full text
            
        Returns:
            str: Section name or "Unknown"
        """
        # Common section patterns
        section_patterns = [
            r'##\s*\d*\.?\s*(Introduction|Abstract)',
            r'##\s*\d*\.?\s*(Methods?|Methodology|Experimental|Materials?\s+and\s+Methods?)',
            r'##\s*\d*\.?\s*(Results?|Findings)',
            r'##\s*\d*\.?\s*(Discussion)',
            r'##\s*\d*\.?\s*(Conclusion|Summary)',
            r'##\s*\d*\.?\s*(References?|Bibliography)',
            r'##\s*\d*\.?\s*(Acknowledgments?|Acknowledgements?)',
            r'##\s*\d*\.?\s*([A-Z][a-zA-Z\s]+)',  # Generic section
        ]
        
        # First, try to find section in the chunk itself
        for pattern in section_patterns:
            match = re.search(pattern, chunk, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # If not found in chunk, look backwards in full text
        if full_text and position > 0:
            # Look at text before this chunk (up to 2000 characters back)
            context_start = max(0, position - 2000)
            context = full_text[context_start:position]
            
            # Find the last section header before this position
            all_matches = []
            for pattern in section_patterns:
                for match in re.finditer(pattern, context, re.IGNORECASE):
                    all_matches.append((match.start(), match.group(1).strip()))
            
            if all_matches:
                # Return the section from the last match
                all_matches.sort(key=lambda x: x[0], reverse=True)
                return all_matches[0][1]
        
        return "Unknown"
    
    def _determine_text_type(self, chunk: str) -> str:
        """
        Determine text type based on keywords.
        
        Detects:
        - table_caption: Contains "Table", "Figure" keywords
        - text: Regular text
        
        Args:
            chunk: Chunk text
            
        Returns:
            str: "text" or "table_caption"
        """
        # Check for table/figure keywords
        table_figure_patterns = [
            r'\bTable\s+\d+',
            r'\bFigure\s+\d+',
            r'\bFig\.\s+\d+',
            r'\bScheme\s+\d+',
        ]
        
        for pattern in table_figure_patterns:
            if re.search(pattern, chunk, re.IGNORECASE):
                return "table_caption"
        
        return "text"
    
    def _extract_doi(self, source: str = None, chunk: str = None) -> Optional[str]:
        """
        Extract DOI from filename or content.
        
        Uses DOI mapping file to validate DOI.
        
        Args:
            source: Source filename
            chunk: Chunk text
            
        Returns:
            Optional[str]: DOI if found, None otherwise
        """
        # Try to extract DOI from filename using mapping
        if source and self.doi_mapping:
            # Check if source matches any PDF filename in the mapping
            for doi, pdf_filename in self.doi_mapping.items():
                # Remove .pdf extension for comparison
                pdf_base = pdf_filename.replace('.pdf', '')
                source_base = source.replace('.md', '').replace('_clean', '').replace('_enhanced', '')
                
                # Check if source contains the PDF base name
                if pdf_base in source_base or source_base in pdf_base:
                    return doi
        
        # Try to extract DOI from chunk content
        if chunk:
            # Common DOI patterns
            doi_patterns = [
                r'doi:\s*(10\.\d{4,}/[^\s]+)',
                r'DOI:\s*(10\.\d{4,}/[^\s]+)',
                r'\b(10\.\d{4,}/[^\s]+)\b',
            ]
            
            for pattern in doi_patterns:
                match = re.search(pattern, chunk, re.IGNORECASE)
                if match:
                    doi = match.group(1).strip()
                    # Clean up DOI (remove trailing punctuation)
                    doi = re.sub(r'[.,;:)\]]+$', '', doi)
                    return doi
        
        return None
    
    def _calculate_position(self, full_text: str, chunk_text: str, start_search_pos: int) -> tuple:
        """
        Calculate start and end positions of chunk in original text.
        
        Uses find() method to backtrack and calculate start_index.
        Handles overlap-induced position offsets.
        
        Args:
            full_text: Original full text
            chunk_text: Chunk text to find
            start_search_pos: Position to start searching from
            
        Returns:
            tuple: (start_index, end_index)
        """
        # Find the chunk in the full text starting from the search position
        start_index = full_text.find(chunk_text, start_search_pos)
        
        # If not found from search position, try from beginning (edge case)
        if start_index == -1:
            start_index = full_text.find(chunk_text)
        
        # If still not found, use approximate position
        if start_index == -1:
            start_index = start_search_pos
            end_index = start_index + len(chunk_text)
        else:
            end_index = start_index + len(chunk_text)
        
        return start_index, end_index
