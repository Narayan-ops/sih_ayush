import React from 'react'
import { Chip } from '@mui/material'
export const ConfidenceBadge: React.FC<{ confidence: 'low' | 'medium' | 'high'; showLabel?: boolean }> = ({ confidence, showLabel = true }) => <Chip size="small" label={`${showLabel ? 'Confidence: ' : ''}${confidence}`} color={confidence === 'high' ? 'success' : confidence === 'medium' ? 'warning' : 'error'} variant="outlined" sx={{ mt: 1.5, textTransform: 'capitalize' }} />
