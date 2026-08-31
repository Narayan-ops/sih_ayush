import React from 'react'
import { Box, Divider, List, ListItem, Typography } from '@mui/material'

interface Citation { chunk_id?: string; source_id: string; section: string; article: string; clause?: string; version_hash?: string; confidence: number }
export const CitationDisplay: React.FC<{ citations: Citation[] }> = ({ citations }) => {
  if (!citations?.length) return null
  const unique = citations.filter((citation, index, all) => index === all.findIndex(item => item.chunk_id === citation.chunk_id))
  return <Box mt={1.5}><Divider /><Typography variant="overline" color="text.secondary" display="block" mt={1}>Cited sources</Typography><List dense disablePadding>{unique.map((citation, index) => <ListItem key={`${citation.source_id}-${index}`} disableGutters><Typography variant="caption" color="text.secondary">[{citation.source_id || 'Unknown'}{citation.section ? `, Section ${citation.section}` : ''}{citation.clause ? `, Clause ${citation.clause}` : citation.article ? `, Article ${citation.article}` : ''}{citation.version_hash ? ` · v${citation.version_hash.slice(0, 8)}` : ''}] · {(citation.confidence * 100).toFixed(0)}% support</Typography></ListItem>)}</List></Box>
}
