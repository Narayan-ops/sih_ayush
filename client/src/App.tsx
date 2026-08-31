import { useState } from 'react'
import { Box, Chip, Divider, Drawer, List, ListItemButton, ListItemText, Paper, Stack, ToggleButton, ToggleButtonGroup, Toolbar, Typography } from '@mui/material'
import { ChatInterface } from './components'
import { apiService } from './services/api'

type Jurisdiction = 'india' | 'international'
const drawerWidth = 256
const questions = ['Can a classical Ayurvedic formulation be patented in India?', 'What ABS obligations apply when sourcing biological resources?', 'What are the patentability criteria under TRIPS?']
const navigation = [
  { label: 'Legal research', icon: '◈', active: true },
  { label: 'Formulation triage', icon: '◇', tag: 'Guided' },
  { label: 'ABS readiness', icon: '◌', tag: 'Soon' },
  { label: 'TKDL prior-art pointer', icon: '⌕', tag: 'Soon' },
]

function App() {
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>('india')
  const [sessionId, setSessionId] = useState<string | undefined>()
  const sendMessage = async (message: string, selected: string) => {
    const response = await apiService.sendMessage({ message, jurisdiction: selected as Jurisdiction, session_id: sessionId })
    setSessionId(response.session_id)
    return response
  }
  const changeJurisdiction = (_event: React.MouseEvent<HTMLElement>, next: Jurisdiction | null) => {
    if (next) { setJurisdiction(next); setSessionId(undefined) }
  }
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', display: 'flex' }}>
      <Drawer variant="permanent" sx={{ width: drawerWidth, '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box', bgcolor: 'primary.main', color: '#eef6ef', border: 0, p: 2 } }}>
        <Stack direction="row" alignItems="center" spacing={1.25} sx={{ p: 1.25, pb: 4 }}>
          <Box sx={{ width: 36, height: 36, border: '1px solid #8caf98', borderRadius: '50%', display: 'grid', placeItems: 'center', color: '#e6ba68', fontSize: 20 }}>ॐ</Box>
          <Box><Typography fontWeight={700} letterSpacing=".08em" fontSize={14}>IP-SAKTI</Typography><Typography color="#afc3b2" fontSize={12}>Sahayak</Typography></Box>
        </Stack>
        <Typography variant="overline" sx={{ px: 1.5, color: '#92a896' }}>Research workspace</Typography>
        <List>{navigation.map(item => (
          <ListItemButton key={item.label} selected={item.active} disabled={!item.active} sx={{ borderRadius: 1, mb: .5, color: '#c9d7ca', '&.Mui-selected': { bgcolor: '#2a5641', color: '#fff' }, '&.Mui-disabled': { opacity: .78, color: '#c9d7ca' } }}>
            {item.icon}<ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 13, ml: 1 }} />
            {item.tag && <Chip label={item.tag} size="small" sx={{ height: 19, fontSize: 9, bgcolor: 'transparent', color: '#a9c0ae' }} />}
          </ListItemButton>
        ))}</List>
        <Paper variant="outlined" sx={{ mt: 3, p: 1.75, bgcolor: '#24513c', color: '#e7f1e8', borderColor: '#41725b' }}><Typography fontSize={12}><Box component="span" color="#70d39b">●</Box> Sovereign processing</Typography><Typography variant="caption" color="#b8cfbc">Default queries stay on self-hosted infrastructure.</Typography></Paper>
        <Typography variant="caption" sx={{ mt: 'auto', p: 1.25, color: '#8aa28f' }}>AYUSH IPR & regulatory guidance<br />Evidence-led • Version-tracked</Typography>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, px: { xs: 2, md: 5 }, pb: 6 }}>
        <Toolbar disableGutters sx={{ height: 72, borderBottom: '1px solid', borderColor: 'divider', justifyContent: 'space-between' }}><Typography variant="caption" color="text.secondary">IP-SAKTI Sahayak / Legal research</Typography><Chip label="● Grounded-answer gate active" size="small" sx={{ color: '#37624c', bgcolor: 'transparent' }} /></Toolbar>
        <Stack direction={{ xs: 'column', lg: 'row' }} justifyContent="space-between" spacing={4} sx={{ py: 6 }}>
          <Box><Typography variant="overline" color="secondary.main" fontWeight={700}>AYURVEDA • INTELLECTUAL PROPERTY • REGULATION</Typography><Typography variant="h1" sx={{ fontSize: { xs: 40, md: 52 }, lineHeight: 1.03, mt: 1 }}>Make each decision<br /><Box component="i" color="secondary.main">traceable.</Box></Typography><Typography color="text.secondary" sx={{ maxWidth: 570, mt: 2, lineHeight: 1.7 }}>Source-grounded guidance for innovators, practitioners and cultivators navigating Ayurveda IP, ABS and regulatory pathways.</Typography></Box>
          <Stack direction="row" spacing={3} alignSelf="end">{[['33', 'authoritative\nsource files'], ['984', 'versioned\nlegal chunks'], ['2', 'separate\njurisdictions']].map(([value, label]) => <Box key={value} sx={{ borderLeft: '1px solid', borderColor: 'divider', pl: 1.5 }}><Typography variant="h5" fontFamily="Georgia" color="primary.main">{value}</Typography><Typography variant="caption" whiteSpace="pre-line" color="text.secondary">{label}</Typography></Box>)}</Stack>
        </Stack>
        <Paper variant="outlined" sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
          <Box><Typography variant="overline" color="text.secondary">Jurisdiction</Typography><ToggleButtonGroup exclusive value={jurisdiction} onChange={changeJurisdiction} size="small" sx={{ display: 'block' }}><ToggleButton value="india">India</ToggleButton><ToggleButton value="international">International</ToggleButton></ToggleButtonGroup></Box>
          <Divider flexItem orientation="vertical" /><Box><Typography variant="overline" color="text.secondary">Answer standard</Typography><Typography variant="body2" fontWeight={700}>Every factual sentence cited</Typography></Box><Divider flexItem orientation="vertical" /><Box><Typography variant="overline" color="text.secondary">Model boundary</Typography><Typography variant="body2" fontWeight={700}>Self-hosted by default</Typography></Box>
        </Paper>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 1fr) 260px' }, gap: 2.5, mt: 2.5 }}>
          <ChatInterface onSendMessage={sendMessage} jurisdiction={jurisdiction} starterQuestions={questions} />
          <Stack spacing={1.5}><Paper variant="outlined" sx={{ p: 2 }}><Typography variant="overline" color="text.secondary">How it works</Typography>{['Choose a jurisdiction', 'Ask or describe your formulation', 'Inspect source-level evidence'].map((step, index) => <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 1.5 }} key={step}><Typography fontFamily="Georgia" color="secondary.main">0{index + 1}</Typography><Typography variant="body2">{step}</Typography></Stack>)}</Paper><Paper variant="outlined" sx={{ p: 2, bgcolor: '#fff0cf', borderColor: '#edcf91' }}><Typography variant="overline" color="text.secondary">Important</Typography><Typography variant="h6" fontFamily="Georgia" fontWeight={400}>Information, not legal advice.</Typography><Typography variant="caption" color="text.secondary">For a filing, opinion or case-specific decision, use a qualified IP professional or AYUSH facilitator.</Typography></Paper><Paper variant="outlined" sx={{ p: 2, bgcolor: '#edf4ec' }}><Typography variant="overline" color="text.secondary">Current scope</Typography><Typography variant="body2" color="text.secondary"><b>{jurisdiction === 'india' ? 'India' : 'International'}</b> corpus only. The system never blends jurisdictions in one answer.</Typography></Paper></Stack>
        </Box>
      </Box>
    </Box>
  )
}
export default App
