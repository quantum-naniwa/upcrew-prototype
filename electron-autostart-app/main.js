const { app, BrowserWindow, ipcMain, powerMonitor, session, systemPreferences } = require('electron')

// ビデオキャプチャが黒くなる問題を防ぐためハードウェアアクセラレーションを無効化
app.disableHardwareAcceleration()
const path = require('path')
const fs = require('fs')

let mainWindow

function getTasksFilePath() {
  return path.join(app.getPath('userData'), 'tasks.json')
}

function loadTasks() {
  const filePath = getTasksFilePath()
  if (!fs.existsSync(filePath)) return []
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
  } catch {
    return []
  }
}

function saveTasks(tasks) {
  fs.writeFileSync(getTasksFilePath(), JSON.stringify(tasks), 'utf-8')
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 380,
    height: 580,
    resizable: false,
    alwaysOnTop: true,
    frame: false,
    transparent: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  mainWindow.loadFile('index.html')
  mainWindow.webContents.openDevTools({ mode: 'detach' })

  // 画面の右下に配置
  const { screen } = require('electron')
  const display = screen.getPrimaryDisplay()
  const { width, height } = display.workAreaSize
  mainWindow.setPosition(width - 400, height - 600)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(() => {
  // カメラ・マイクの許可リクエストを自動承認
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') {
      callback(true)
    } else {
      callback(false)
    }
  })

  // PC起動時・ログイン時に自動起動する設定
  app.setLoginItemSettings({
    openAtLogin: true,
    openAsHidden: false
  })

  // macOSにカメラ許可を明示的に要求
  if (process.platform === 'darwin') {
    const cameraStatus = systemPreferences.getMediaAccessStatus('camera')
    console.log('Camera access status:', cameraStatus)
    if (cameraStatus !== 'granted') {
      systemPreferences.askForMediaAccess('camera').then(granted => {
        console.log('Camera permission granted:', granted)
      })
    }
  }

  createWindow()

  // スリープ復帰後の画面ロック解除時にウィンドウを表示＆撮影
  powerMonitor.on('unlock-screen', () => {
    if (mainWindow === null) {
      createWindow()
    } else {
      mainWindow.show()
    }
    if (mainWindow) {
      mainWindow.webContents.send('take-photo')
    }
  })
})

ipcMain.on('minimize-window', () => {
  if (mainWindow) mainWindow.minimize()
})

ipcMain.on('close-window', () => {
  if (mainWindow) mainWindow.close()
})

ipcMain.handle('get-tasks', () => loadTasks())

ipcMain.on('save-tasks', (_, tasks) => saveTasks(tasks))

ipcMain.on('save-recording', (_, buffer) => {
  const moviesDir = app.getPath('videos')
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const filePath = path.join(moviesDir, `recording-${timestamp}.webm`)
  fs.writeFileSync(filePath, buffer)
  console.log('Recording saved:', filePath)
})

app.on('window-all-closed', () => {
  // unlock-screen イベントを引き続き受け取るためアプリは終了しない
})
