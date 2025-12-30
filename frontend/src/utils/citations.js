/**
 * Citation Parser and Utilities
 * Handles parsing [citation:chunk_id] tags from AI responses
 */

/**
 * Parse citations from AI response content
 * @param {string} content - The AI response text with citation tags
 * @returns {{ cleanContent: string, citations: Array<{id: string, position: number, index: number}> }}
 */
export function parseCitations(content) {
  if (!content) {
    return { cleanContent: '', citations: [] };
  }

  const citationRegex = /\[citation:(chunk_\d+)\]/g;
  const citations = [];
  let citationIndex = 1;
  let lastChunkId = null;

  // Find all citations and their positions
  let match;
  while ((match = citationRegex.exec(content)) !== null) {
    const chunkId = match[1];

    // Assign sequential numbers, but reuse number for repeated citations
    let assignedIndex;
    const existingCitation = citations.find(c => c.id === chunkId);
    if (existingCitation) {
      assignedIndex = existingCitation.index;
    } else {
      assignedIndex = citationIndex++;
    }

    citations.push({
      id: chunkId,
      position: match.index,
      index: assignedIndex,
      fullMatch: match[0],
    });
  }

  // Replace citations with numbered superscripts
  let cleanContent = content;
  // Process in reverse order to preserve positions
  const sortedCitations = [...citations].sort((a, b) => b.position - a.position);
  for (const citation of sortedCitations) {
    cleanContent = cleanContent.replace(
      citation.fullMatch,
      `[${citation.index}]`
    );
  }

  // Deduplicate citations for the citation list
  const uniqueCitations = [];
  const seenIds = new Set();
  for (const citation of citations) {
    if (!seenIds.has(citation.id)) {
      seenIds.add(citation.id);
      uniqueCitations.push({
        id: citation.id,
        index: citation.index,
      });
    }
  }

  return {
    cleanContent,
    citations: uniqueCitations,
  };
}

/**
 * Extract all unique chunk IDs from content
 * @param {string} content - The AI response text
 * @returns {string[]} Array of unique chunk IDs
 */
export function extractCitationIds(content) {
  if (!content) return [];

  const regex = /\[citation:(chunk_\d+)\]/g;
  const ids = new Set();
  let match;

  while ((match = regex.exec(content)) !== null) {
    ids.add(match[1]);
  }

  return Array.from(ids);
}

/**
 * Build a mapping from chunk IDs to source data
 * @param {Array} sources - Array of source objects from the backend
 * @returns {Map<string, object>} Map of chunk_id -> source data
 */
export function buildSourceMap(sources) {
  const map = new Map();

  if (!sources || !Array.isArray(sources)) {
    return map;
  }

  for (const source of sources) {
    if (source.chunk_id) {
      map.set(source.chunk_id, {
        chunkId: source.chunk_id,
        citationNumber: source.citation_number,
        documentId: source.document_id,
        documentTitle: source.document_title || 'Unknown Document',
        contentPreview: source.content_preview || source.content?.substring(0, 200) || '',
        content: source.content || '',
        page: source.page,
        sourceType: source.source_type,
      });
    }
  }

  return map;
}

/**
 * Get source data for a specific citation
 * @param {string} chunkId - The chunk ID
 * @param {Map} sourceMap - The source map from buildSourceMap
 * @returns {object|null} Source data or null if not found
 */
export function getSourceForCitation(chunkId, sourceMap) {
  return sourceMap.get(chunkId) || null;
}

/**
 * Format citation number for display
 * @param {number} index - The citation index (1-based)
 * @returns {string} Formatted citation string
 */
export function formatCitationNumber(index) {
  return `[${index}]`;
}

/**
 * Check if content has any citations
 * @param {string} content - The content to check
 * @returns {boolean} True if content contains citations
 */
export function hasCitations(content) {
  if (!content) return false;
  return /\[citation:chunk_\d+\]/.test(content);
}

/**
 * Strip all citations from content
 * @param {string} content - The content with citations
 * @returns {string} Content without citation tags
 */
export function stripCitations(content) {
  if (!content) return '';
  return content.replace(/\[citation:chunk_\d+\]/g, '').replace(/\s+/g, ' ').trim();
}

/**
 * Format source type for display
 * @param {string} sourceType - The source type (journal, chat, upload)
 * @returns {string} Human-readable source type
 */
export function formatSourceType(sourceType) {
  const types = {
    journal: 'Journal Entry',
    chat: 'Conversation',
    upload: 'Document',
  };
  return types[sourceType] || 'Source';
}

/**
 * Get icon for source type
 * @param {string} sourceType - The source type
 * @returns {string} Icon name or emoji
 */
export function getSourceTypeIcon(sourceType) {
  const icons = {
    journal: 'pencil',
    chat: 'message-circle',
    upload: 'file-text',
  };
  return icons[sourceType] || 'file';
}
