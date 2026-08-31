import { createTheme } from '@mui/material/styles'

export const appTheme = createTheme({
  palette: {
    mode: 'light', primary: { main: '#173d2e', dark: '#0d2b1e', light: '#e9f0e9' },
    secondary: { main: '#b98635' }, background: { default: '#f5f5ef', paper: '#fffdf8' }, text: { primary: '#17271f', secondary: '#64756c' },
  },
  typography: { fontFamily: 'Manrope, Arial, sans-serif', h1: { fontFamily: 'Georgia, serif', fontWeight: 400, letterSpacing: '-0.045em' }, h2: { fontFamily: 'Georgia, serif', fontWeight: 400 } },
  shape: { borderRadius: 10 },
  components: { MuiButton: { defaultProps: { disableElevation: true } }, MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } } },
})
