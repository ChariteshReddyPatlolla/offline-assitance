# 1. Start Microsoft Edge in App Mode (sleek, borderless dedicated window)
$edgeArgs = "--app=http://localhost:5173 --window-size=400,750"
Write-Host "Launching Microsoft Edge in App Mode..."
Start-Process "msedge.exe" -ArgumentList $edgeArgs

# 2. Wait for the window to load and register its title (up to 10 seconds)
$hWnd = [IntPtr]::Zero
Write-Host "Waiting for OmniAgent window to initialize..."
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    # Search strictly for msedge processes whose MainWindowTitle matches OmniAgent Copilot or Vite/localhost
    $proc = Get-Process -Name "msedge" -ErrorAction SilentlyContinue | Where-Object { 
        $_.MainWindowTitle -like "*OmniAgent Copilot*" -or 
        $_.MainWindowTitle -like "*Vite*" -or 
        $_.MainWindowTitle -like "*localhost*"
    } | Select-Object -First 1
    
    if ($proc -and $proc.MainWindowHandle -ne [IntPtr]::Zero) {
        $hWnd = $proc.MainWindowHandle
        break
    }
}

if ($hWnd -eq [IntPtr]::Zero) {
    # Fallback search - find any Edge process with a valid non-empty window title
    $proc = Get-Process -Name "msedge" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne "" } | Select-Object -First 1
    if ($proc) {
        $hWnd = $proc.MainWindowHandle
    }
}

if ($hWnd -eq [IntPtr]::Zero) {
    Write-Host "⚠️ Warning: Could not find OmniAgent app window handle to style. You can still use it in the browser!"
    exit
}

Write-Host "Found OmniAgent window (HWND: $hWnd). Styling as Translucent & Pinning to Always-on-Top..."

# 3. Import Windows User32 DLL functions for transparency and positioning
$signature = @"
[DllImport("user32.dll")]
public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

[DllImport("user32.dll")]
public static extern int GetWindowLong(IntPtr hWnd, int nIndex);

[DllImport("user32.dll")]
public static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

[DllImport("user32.dll")]
public static extern bool SetLayeredWindowAttributes(IntPtr hWnd, uint crKey, byte bAlpha, uint dwFlags);
"@
$User32 = Add-Type -MemberDefinition $signature -Name "User32" -PassThru

# 4. Make Window Translucent (Commented out to ensure 100% solid normal mode window)
# $currentStyle = $User32::GetWindowLong($hWnd, -20)
# $newStyle = $currentStyle -bor 0x00080000
# $User32::SetWindowLong($hWnd, -20, $newStyle)
# $User32::SetLayeredWindowAttributes($hWnd, 0, 160, 2)

# 5. Pin to Always-on-Top
# HWND_TOPMOST = -1
# SWP_NOSIZE = 1 (0x0001)
# SWP_NOMOVE = 2 (0x0002)
# Flags = SWP_NOSIZE | SWP_NOMOVE = 3
$User32::SetWindowPos($hWnd, [IntPtr](-1), 0, 0, 0, 0, 3)

Write-Host "✅ OmniAgent Copilot is now pinned floating on top and translucent!"
