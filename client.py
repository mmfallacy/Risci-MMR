import sys,configparser,os,subprocess,yaml,socket,time,threading
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton,
                             QHBoxLayout,QFrame, QLabel, QVBoxLayout,QShortcut,
							 QStackedWidget,QAbstractButton,QGraphicsOpacityEffect,
							 QStackedLayout,QMessageBox)
from PyQt5.QtGui import (QFont,QPixmap,QKeySequence,QColor,QPalette,QPainter,QFontDatabase)
from PyQt5.QtCore import (QObject,Qt,QUrl,QEvent,QPropertyAnimation,QEasingCurve,QTimer,QThread,pyqtSignal)
from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
from PyQt5 import QtWidgets
from functools import partial
from win32gui import GetWindowText, GetForegroundWindow,SetForegroundWindow

app = QApplication(sys.argv)
dim = app.primaryScreen().size()

def currentDir():
    ####        ===========  CHECK IF FROZEN  ===========
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(__file__)
def rPix(value):
	return (dim.height()/1080)*value
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
iniObj = configparser.ConfigParser()
iniObj.read(os.path.join(currentDir(), 'resources\config.ini'))
id = iniObj['Client_Data']['id']## Judge Number
winStat = int(iniObj['Client_Data']['status']) ## Window Status: Always on Top-1
tconNum=int(iniObj['Client_Data']['conNum']) ## Total No. Contestants
istream = open(os.path.join(currentDir(), 'resources\data\contestants.yml'))
conObj = yaml.load(istream)
con = conObj['contestants']
order = con[-1]["order"]
order = [i.upper() for i in order]

istreamPalette = open(os.path.join(currentDir(), 'resources\data\palette.yml'))
scheme = yaml.load(istreamPalette)
Serv_Data = [iniObj['Serv_Data']['Serv_IP'],int(iniObj['Serv_Data']['Serv_PORT']),int(iniObj['Serv_Data']['buffSize'])] ## [ IP , PORT , BUFFER ]

QFontDatabase.addApplicationFont("resources/fonts/Roboto-Regular.ttf")
QFontDatabase.addApplicationFont("resources/fonts/Montserrat-Regular.otf")

fonts = ["Roboto","Montserrat","Lucida Console"]
styles = {	
	"noframe":"""
					.QFrame#noframe{
					background-color: rgb(255,255,255,0);
					}
			""",
	"mask":"""
					.QFrame#mask{
					background-image: url("resources/img/background/mask.png");
					}
			""",
	"mainMenu":"""
					.QWidget#main{
					border-image: url("resources/img/background.png");
					}
			""",
		}
	
def adaptiveStyle(obj,palette = "white"): ##Returns stylesheet with adaptive palette
	sheet = {
			"buttonFrame":"""
					.QFrame#buttonFrame{
					background-color: %s;
					border-bottom-left-radius:%spx;
					border-bottom-right-radius:%spx;
					}
			""" % (palette,rPix(3),rPix(3)),
			"selector" : """
					.QFrame#selector{
					background: %s;
					border-radius: %spx;
					}
			""" % (palette,rPix(10)),
			}
	return sheet[obj]
	
def stackSelectorState(stackSelector, state):
	if state ==0:## normal
		stackSelector.setStyleSheet("""
						.QPushButton{
						background: white;
						border-radius: %spx;
						
						}
						.QPushButton:disabled{
						background: black;
						border-radius: %spx;
						
						}
				""" % (rPix(4),rPix(4)))
	elif state == 1: ## saved
		stackSelector.setStyleSheet("""
						.QPushButton{
						background: lightgreen;
						border-radius: %spx;
						
						}
						.QPushButton:disabled{
						background: black;
						border-radius: %spx;
						
						}
				""" % (rPix(4),rPix(4)))
	elif state == 2: ## not saved
		stackSelector.setStyleSheet("""
						.QPushButton{
						background: red;
						border-radius: %spx;
						
						}
						.QPushButton:disabled{
						background: black;
						border-radius: %spx;
						
						}
				""" % (rPix(4),rPix(4)))
	
class ResourceManager(): ## Manages pixmap resources (img, background)
	def __init__(self):
		self.loaded = False
		self.bg = []
		self.ui=scheme["ui"]
		self.buttonPanelPalette=scheme["background"]
		self.backgroundPalette=scheme["background"]
		self.mask = QPixmap("")
		self.images={}
		self.buttons=[]
		self.totalImgNum = 9
		## LOAD IMAGES: (x005) 
		self.progress =0
		inc = 100 /((tconNum*self.totalImgNum)+4)
		if "-noimg" not in sys.argv:
			for conNum in range(1,tconNum+1):
				self.images[str(conNum)] = []
				for i in range(0,self.totalImgNum):
					if os.path.isfile(os.path.join(currentDir(),"resources/data/"+str(conNum)+"/"+str(i)+".jpg")):
						_pixmap = QPixmap("resources/data/"+str(conNum)+"/"+str(i)+".jpg")
						w = min(rPix(760), _pixmap.width())
						h = min(rPix(845), _pixmap.height())
						self.images[str(conNum)].append(_pixmap.scaled(w,h,Qt.KeepAspectRatio))
					self.progress +=inc
					barInc = int((70/100)*self.progress)
					print("|"+"/"*barInc+" "*(70-barInc)+"|"+" {0:.2f}%".format(self.progress),end="\r")
					
		## LOAD BG:
		for i in range(0,4):
			_pixmap = QPixmap("resources/img/background/"+str(i)+".png")
			w = min(rPix(1601), _pixmap.width())
			h = min(rPix(885), _pixmap.height())
			self.bg.append(_pixmap.scaled(w,h,Qt.IgnoreAspectRatio))
			self.progress+=inc
			barInc = int((70/100)*self.progress)
			print("|"+"/"*barInc+" "*(70-barInc)+"|"+" {0:.2f}%".format(self.progress),end="\r")
		
		print("\nDone Loading Resources")
		print('Size: %d x %d' % (dim.width(), dim.height()))
	def isLoaded(self):
		return self.loaded
class ImageButton(QAbstractButton): ## Sets Button as an image and animates(hover,pressed,disabled) USAGE: ImageButton(Resource Directory, Width, Height)
	def __init__(self,resdir,width,height,toggle=True,tooltip=False, parent=None):
		super(ImageButton, self).__init__(parent)
		self.isHover = False
		self._states = [] 
		self.currentState =0
		if toggle:
			tStates =5
		else:
			tStates =4
		for i in range(1,tStates):
			if os.path.isfile(os.path.join(resdir,str(i)+".png")):
				_pixmap = QPixmap(os.path.join(resdir,str(i)+".png"))
				w = min(width, _pixmap.width())
				h = min(height, _pixmap.height())
				self._states.append(_pixmap.scaled(w,h,Qt.KeepAspectRatio))
		self.setFixedSize(width,height)
		if tooltip:
			self.setToolTip(tooltip)
	def paintEvent(self, event):
		_painter = QPainter()
		_painter.begin(self)
		try:
			_painter.drawPixmap( (self.width() - self._states[self.currentState].width()) / 2,(self.height() - self._states[self.currentState].height())/2, self._states[self.currentState])
		except:
			pass
		_painter.end()
	def mousePressEvent(self,event): ## MOUSE PRESS
		super().mousePressEvent(event)
		if not self.isEnabled():
			self.currentState =3
		else:	
			self.currentState =2
		self.update()
	def mouseReleaseEvent(self,event): ## MOUSE RELEASE
		super().mouseReleaseEvent(event)
		if not self.isEnabled():
			self.currentState =3
		else:
			self.currentState =0
		self.update()
	def enterEvent(self, event): ## MOUSE HOVER
		self.isHover = True
		if not self.isEnabled():
			self.currentState =3
		else:	
			self.currentState =1
		self.update()
	def leaveEvent(self, event): ## AFTER MOUSE HOVER
		self.isHover = False
		if not self.isEnabled():
			self.currentState =3
		else:	
			self.currentState =0
		self.update()
	def setEnabled_(self,bool):
		self.setEnabled(bool)
		if bool:
			self.currentState = 1
		else:
			self.currentState = 3
		self.update()
class ImageFrame(QFrame): ## Sets Image as Frame Background
	def __init__(self,fade = False,default=False):
		super().__init__()
		self.pixmap = False
		self.fade = fade
		self.runFade = fade
	def paintEvent(self, event):
		#super(ImageFrame,self).paintEvent(event)
		if self.pixmap:
			_painter = QPainter()
			_painter.begin(self)
			_painter.setOpacity(1)
			if self.runFade:
				self.fadeIn()
			_painter.drawPixmap( (self.width() - self.pixmap.width()) / 2,(self.height() - self.pixmap.height())/2, self.pixmap)
			_painter.end()
	def setPixmap(self,pixmap,ap=0):
		if ap==2:
			self.pixmap = pixmap.scaled(self.width(),self.height(),Qt.IgnoreAspectRatio)
		elif ap==1:
			self.pixmap = pixmap.scaled(self.width(),self.height(),Qt.KeepAspectRatio)
		else:
			self.pixmap = pixmap
		if self.fade:
			self.runFade = True
		self.update()
	def fadeIn(self):
		effect = QGraphicsOpacityEffect()
		self.setGraphicsEffect(effect)

		self.anim = QPropertyAnimation(effect, b"opacity")
		self.anim.setDuration(500)
		self.anim.setStartValue(0)
		self.anim.setEndValue(1)
		self.anim.setEasingCurve(QEasingCurve.InBack)
		self.anim.start()	
		self.runFade = False 
class cStack(QWidget): ## Widget for every contestant
	def __init__(self, conNum,res,bg):
		super().__init__()
		self.conNum = conNum
		self.scores =None
		self.imgNum = 0
		self.setFixedSize(rPix(1600),rPix(885))
		## Renames passed ResourceManager() object 
		self.res = res
		## Loads Pixmaps
		self.bg=bg
		self.ui=self.res.ui
		self.pixmaps = self.res.images
		self.runOnce =False
		self.callback_value = None
		self.initUI()
	def initUI(self):
		## Information Labels:
		infoLabel1 = QLabel() ## NAME
		infoLabel1.setText(con[self.conNum-1][0][0]["name"].upper())
		infoLabel1.setFont(QFont(fonts[1], rPix(25),weight=75))
		
		infoLabel2 = QLabel()
		infoLabel2.setText(con[self.conNum-1][1][0]["name"].upper())
		infoLabel2.setFont(QFont(fonts[1], rPix(25),weight=75))
		
		infoLabel3 = QLabel() ## SECTION
		if con[self.conNum-1][0][1]["section"] == con[self.conNum-1][1][1]["section"]:
			infoLabel3.setText(str(con[self.conNum-1][2]["grade"])+ " - " + con[self.conNum-1][0][1]["section"])
		else: 
			infoLabel3.setText(str(con[self.conNum-1][2]["grade"])+ " - " + con[self.conNum-1][0][1]["section"] + " & " + con[self.conNum-1][1][1]["section"])
		infoLabel3.setFont(QFont(fonts[0], rPix(15),weight=75))
		
		infoLabelLayout = [QHBoxLayout(),QHBoxLayout(),QHBoxLayout()] ## Centralize Using Horizontal Box Layout
		for i in infoLabelLayout:
			i.setContentsMargins(0,0,0,0)
			i.setSpacing(0)
		infoLabelLayout[0].addStretch()
		infoLabelLayout[0].addWidget(infoLabel1)
		infoLabelLayout[0].addStretch()
		infoLabelLayout[1].addStretch()
		
		infoLabelLayout[1].addWidget(infoLabel2)
		infoLabelLayout[1].addStretch()
		
		infoLabelLayout[2].addStretch()
		infoLabelLayout[2].addWidget(infoLabel3)
		infoLabelLayout[2].addStretch()
		
		## Information Layout:
		infoLayout = QVBoxLayout()
		infoLayout.setSpacing(10)
		for i in infoLabelLayout:
			infoLayout.addLayout(i)
		## Information Frame: 
		infoFrame = QFrame()
		infoFrame.setFixedSize(rPix(780),rPix(205))
		infoFrame.setObjectName("infoFrame")
		infoFrame.setStyleSheet(".QFrame#infoFrame{border-bottom:2px #A9A9A9;background:"+ self.ui[(self.conNum-1)%4]+";border-radius : 5px}")
		infoFrame.setLayout(infoLayout)
		
		## Score Sheet Webview: 
		if "-nosheet" in sys.argv:
			self.sheet = QFrame()
			self.sheet.setFixedSize(rPix(760),rPix(630))
		else:
			self.sheet = QWebView()
			self.sheet.loadFinished.connect(self.pageLoaded)
			_path= QUrl.fromLocalFile(currentDir()+"/resources/sheet.html")
			self.sheet.load(_path)
		
		## Navigation Buttons
		resetButton = ImageButton("resources/img/buttons/reset",rPix(30),rPix(30),toggle=False,tooltip="<b>Reset Scores</b>")
		
		
		saveButton = ImageButton("resources/img/buttons/save",rPix(30),rPix(30),toggle=False,tooltip="<b>Save Scores</b>")
		
		if "-nosheet" not in sys.argv:
			resetButton.clicked.connect(self.resetScores)
			saveButton.clicked.connect(self.saveScores)
		
		## Sheet Navigation Layout:
		sheetNavigationLayout = QHBoxLayout()
		sheetNavigationLayout.addStretch()
		sheetNavigationLayout.addWidget(resetButton)
		sheetNavigationLayout.addWidget(saveButton)
		
		## Layout of Sheet Frame:
		sheetLayout = QVBoxLayout()
		sheetLayout.setContentsMargins(rPix(15),rPix(10),rPix(10),rPix(10))
		sheetLayout.setSpacing(rPix(5))
		sheetLayout.addWidget(self.sheet)
		sheetLayout.addLayout(sheetNavigationLayout)
		
		## Sheet Frame:
		sheetFrame = QFrame()
		sheetFrame.setFixedSize(rPix(780),rPix(650))
		sheetFrame.setObjectName("sheetFrame")
		sheetFrame.setStyleSheet(".QFrame#sheetFrame{border-bottom:2px #A9A9A9;background:"+ self.ui[(self.conNum-1)%4]+";border-radius : 5px}")
		sheetFrame.setLayout(sheetLayout)
		
		## Left Placeholder Layout:
		leftLayout = QVBoxLayout()
		leftLayout.setContentsMargins(0,0,0,0)
		leftLayout.setSpacing(10)
		leftLayout.addWidget(infoFrame)
		leftLayout.addWidget(sheetFrame)
		
		
		## Previous Image Button:
		prevImage = ImageButton("resources/img/buttons/prevImg",rPix(100),rPix(845),toggle=False,tooltip="<b>Previous Image</b>")
		prevImage.clicked.connect(self.prevImageEvt)
		
		
		## Next Image Button:
		nextImage = ImageButton("resources/img/buttons/nextImg",rPix(100),rPix(845),toggle=False,tooltip="<b>Next Image</b>")
		nextImage.clicked.connect(self.nextImageEvt)
		##Con Num Label:
		conNumLabel = QLabel(str(self.conNum))
		conNumLabel.setFont(QFont(fonts[0],rPix(30)))
		
		##Con Num Layout:
		conNumLabelLayout = QHBoxLayout()
		conNumLabelLayout.setContentsMargins(0,0,0,0)
		conNumLabelLayout.setSpacing(0)
		conNumLabelLayout.addStretch()
		conNumLabelLayout.addWidget(conNumLabel)
		conNumLabelLayout.addStretch()
		
		## Label for info
		self.infoconLabel = QLabel("NO IMAGE LOADED")
		self.infoconLabel.setFont(QFont(fonts[1],rPix(10)))
		
		##Con Num Layout:
		infoconLabelLayout = QHBoxLayout()
		infoconLabelLayout.setContentsMargins(0,0,0,0)
		infoconLabelLayout.setSpacing(0)
		infoconLabelLayout.addStretch()
		infoconLabelLayout.addWidget(self.infoconLabel)
		infoconLabelLayout.addStretch()
		
		##Vertical Layout for conNum and Info
		vertConInfoLayout = QVBoxLayout()
		vertConInfoLayout.setContentsMargins(0,0,0,0)
		vertConInfoLayout.setSpacing(rPix(20))
		vertConInfoLayout.addStretch()
		vertConInfoLayout.addLayout(conNumLabelLayout)
		vertConInfoLayout.addLayout(infoconLabelLayout)
		vertConInfoLayout.addStretch()
		
		
		## Image Info Frame:
		infoFrame = ImageFrame()
		_infoPixmap = QPixmap("resources/img/infoFrame.png")
		infoFrame.setPixmap(_infoPixmap.scaled(rPix(560),rPix(120),Qt.KeepAspectRatio))	
		infoFrame.setLayout(vertConInfoLayout)
		
		## Image Info Filler:
		infoFiller = QLabel()
		infoFiller.setFixedSize(rPix(560),rPix(727))
		
		## Image Info Layout:
		infoLayout = QVBoxLayout()
		infoLayout.addWidget(infoFiller)
		infoLayout.addWidget(infoFrame)
		infoLayout.setContentsMargins(0,0,0,0)
		infoLayout.setSpacing(0)
		
		
		## Image Navigation/Info Layout:
		navigLayout = QHBoxLayout()
		navigLayout.addWidget(prevImage)
		navigLayout.addLayout(infoLayout)
		navigLayout.addWidget(nextImage)
		navigLayout.setContentsMargins(0,0,0,0)
		navigLayout.setSpacing(0)
		
		## Image Navigation/Info Frame:
		navigFrame = QFrame()
		navigFrame.setObjectName("noframe")
		navigFrame.setStyleSheet(styles["noframe"])
		navigFrame.setLayout(navigLayout)
		
		
		## Image Frame:
		self.imageFrame = ImageFrame(fade=True)
		try: ##Checks if Pixmap is available, then sets it
			self.imageFrame.setPixmap(self.pixmaps[str(self.conNum)][self.imgNum])
			self.infoconLabel.setText(order[self.imgNum])
		except:
			pass
		self.imageFrame.setFixedSize(rPix(760),rPix(845))
		
		
		#self.imageFrame.setLayout(navigLayout)
		## Image Stacked Layout:
		imageStacked = QStackedLayout()
		imageStacked.setStackingMode(QStackedLayout.StackAll)
		imageStacked.setContentsMargins(0,0,0,0)
		imageStacked.setSpacing(0)
		imageStacked.insertWidget(0,self.imageFrame)
		imageStacked.insertWidget(1,navigFrame)
		
		## Image Placeholder Layout:
		imagePlaceholderLayout = QHBoxLayout()
		imagePlaceholderLayout.setContentsMargins(rPix(15),rPix(10),rPix(10),rPix(10))
		imagePlaceholderLayout.setSpacing(0)
		imagePlaceholderLayout.addLayout(imageStacked)
		
		## Image Placeholder Frame
		imagePlaceholderFrame = QFrame()
		imagePlaceholderFrame.setObjectName("imageplaceholder")
		imagePlaceholderFrame.setStyleSheet(".QFrame#imageplaceholder{border-bottom:2px #A9A9A9;background:"+ self.ui[(self.conNum-1)%4]+";border-radius : 5px}")
		imagePlaceholderFrame.setFixedSize(rPix(780),rPix(865))
		imagePlaceholderFrame.setLayout(imagePlaceholderLayout)
		
		## Main Layout:
		mainLayout = QHBoxLayout()
		mainLayout.setContentsMargins(rPix(10),rPix(10),rPix(10),rPix(10))
		mainLayout.setSpacing(10)
		
		## Dynamic Layouting (based on Contestant Number)
		if self.conNum <= (tconNum/2):
			mainLayout.addLayout(leftLayout)
			mainLayout.addWidget(imagePlaceholderFrame)
		else:
			mainLayout.addWidget(imagePlaceholderFrame)
			mainLayout.addLayout(leftLayout)
			
		## Background Frame:
		mainFrame = ImageFrame()
		mainFrame.setPixmap(self.bg)
		mainFrame.setLayout(mainLayout)
		
		## Placeholder Layout:
		placeholderLayout = QHBoxLayout()
		placeholderLayout.setContentsMargins(0,0,0,0)
		placeholderLayout.setSpacing(0)
		placeholderLayout.addWidget(mainFrame)
		
		self.setLayout(placeholderLayout)
		
	def prevImageEvt(self):
		self.imgNum = (self.imgNum -1)% self.res.totalImgNum
		try: ##Checks if Pixmap is available, then sets it
			self.imageFrame.setPixmap(self.pixmaps[str(self.conNum)][self.imgNum])
			self.infoconLabel.setText(order[self.imgNum])
		except:
			pass
	def nextImageEvt(self):
		self.imgNum = (self.imgNum +1)% self.res.totalImgNum
		try: ##Checks if Pixmap is available, then sets it
			self.imageFrame.setPixmap(self.pixmaps[str(self.conNum)][self.imgNum])
			self.infoconLabel.setText(order[self.imgNum])
		except:
			pass
	def callback(self, value):
		self.callback_value = value
	def save_callback(self,value):
		_html = self.sheet.page()
		if value == "error":
			print("error")
		else:
			try:
				female = [int(i) for i in value.split('~')[0].split("-")]
				male = [int(i) for i in value.split('~')[1].split("-")]
				pair = [int(i) for i in value.split('~')[2].split("-")]
				scores = {"pair" : pair, "female":female,"male" : male}
				ostream = {"scores":scores}
				with open(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(self.conNum)+".yml"),"w+") as _f:
					yaml.dump(ostream,_f, default_flow_style=False)
			except:
				pass
	def pageLoaded(self): ## Runs Functions on Page Load()
		if not self.runOnce:
			self.runOnce = True
			self.setBG()
			self.runOnce = False
		else:
			self.runOnce = False	
	def activate(self):
		if "-nosheet" not in sys.argv and os.path.isfile(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(self.conNum)+".yml")):
			self.loadScores()
	def setBG(self): ## Sets background of sheet based on UI Color (x007)
		palette = self.res.ui[(self.conNum-1)%4]
		_html = self.sheet.page()
		_html.runJavaScript('setBackground("' + palette +'");', self.callback)
	def resetScores(self):
		_html = self.sheet.page()
		if os.path.isfile(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(self.conNum)+".yml")):
			alertReply = QMessageBox.warning(self, 'Are you sure?', "Do you want to Reset Fields? Press the Reset option to clear fields only", QMessageBox.Yes | QMessageBox.Reset | QMessageBox.No, QMessageBox.No)
			if alertReply == QMessageBox.Yes:
				_html.runJavaScript('clearFields();',self.callback)
				os.remove(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(self.conNum)+".yml"))
			if alertReply == QMessageBox.Reset:
				_html.runJavaScript('clearFields();',self.callback)
			if alertReply == QMessageBox.No:
				return
		else:
			_html.runJavaScript('alert("Cannot Reset scores! No scoresheet saved.");',self.callback)
	def loadScores(self): ## Loads Saved Scores
		with open(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(self.conNum)+".yml")) as _f:
			_istream= yaml.load(_f)
		scores =_istream["scores"]
		female = [str(i) for i in scores["female"] ]
		male = [str(i) for i in scores["male"] ]
		pair = [str(i) for i in scores["pair"] ]
		
		scoreList = "-".join(female)+"~"+"-".join(male)+"~"+"-".join(pair);
		_html = self.sheet.page()
		_html.runJavaScript('loadScores("' + scoreList + '");',self.callback)
		print("Scores for Contestant # " + str(self.conNum) + " Loaded.")
	def saveScores(self):
		_html = self.sheet.page()
		self.scores = ""
		_html.runJavaScript('saveScores();',self.save_callback)
class mainWidget(QWidget):
	def __init__(self,resObject):
		super().__init__()
		self.setWindowTitle("mainwidget")
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._magicList = []
		self.uploaded = False
		self.isConnected = False
		
		self.dim = (dim.height() - rPix(70), dim.width() - rPix(320)) ##1010,1600
		self.setFixedSize(self.dim[1],self.dim[0])
		
		self.stackIndex = 0
		## Adopting global Resource Object
		self.res = resObject
		
		self.terminate =False
		## Setting Attributes
		if winStat:
			self.setWindowFlags(Qt.FramelessWindowHint)#|Qt.WindowStaysOnTopHint)
		else:
			self.setWindowFlags(Qt.FramelessWindowHint)
		self.installEventFilter(self)
		
		self.setAttribute(Qt.WA_TranslucentBackground, True)
		self.setFocusPolicy(Qt.StrongFocus)
		self.setFocus()
		
		## Ctrl + W Exit Shortcut
		self.shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
		self.shortcut.activated.connect(self.closeApp)
		self.shortcut2 = QShortcut(QKeySequence("Ctrl+R"), self)
		self.shortcut2.activated.connect(self.resetStackColor)
		
		self.stack = QStackedWidget()
		
		##Creating multiple instances of cStack
		self.stackList = [cStack(i,self.res,self.res.bg[(i-1)%4]) for i in range(1,tconNum+1)]
		
		##Initializing Main Stack
		self.mainStack = QWidget()
		self.mainStackUI()
		
		## Adding cStack instances to StackedWidget
		self.stack.addWidget(self.mainStack)
		for i in self.stackList:
			self.stack.addWidget(i)
		
		## Stack Frame Placeholder

		stackFrameLayout = QHBoxLayout()
		stackFrameLayout.addWidget(self.stack)
		stackFrameLayout.setSpacing(0)
		stackFrameLayout.setContentsMargins(0,0,0,0)
		
		stackFrame = QFrame()
		stackFrame.setLayout(stackFrameLayout)
		
		## Stack Buttons MAIN (prev and next stack)
		
		self.nextStack = ImageButton("resources/img/buttons/nextC",rPix(50),rPix(50),toggle=True,tooltip="<b>Next Contestant</b>")
		self.nextStack.clicked.connect(self.nextEvt)
		
		self.prevStack = ImageButton("resources/img/buttons/prevC",rPix(50),rPix(50),toggle=True,tooltip="<b>Previous Contestant</b>")
		self.prevStack.clicked.connect(self.prevEvt)
		
		## Stack Buttons (MAIN - 14)
		self.stackSelector = [QPushButton() for i in range(0,tconNum+1)]
		
		selectorHLayout = QHBoxLayout()
		selectorHLayout.setSpacing(rPix((14/tconNum)*20))
		selectorHLayout.setContentsMargins(0,rPix(5),0,rPix(5))
		
		##STYLING STACK SELECTORS
		for i in range(0,len(self.stackSelector)):
			self.stackSelector[i].setFixedSize(rPix((14/tconNum)*50),rPix(20))
			stackSelectorState(self.stackSelector[i],0)
			self.stackSelector[i].setFont(QFont(fonts[2]))
			self.stackSelector[i].setText(str(i))
			_temp = partial(self.stackSelectorEvt,i)
			self.stackSelector[i].clicked.connect(_temp)
			selectorHLayout.addWidget(self.stackSelector[i])
			
		## Setting first stack selector as Main Widget
		self.stackSelector[0].setText("MAIN")
		self.stackSelector[0].setFont(QFont(fonts[0],rPix(10)))
		self.stackSelector[0].clicked.connect(lambda: self.stackSelectorEvt(0))
		
		## Stack Selector Frame
		self.selectorFrame = QFrame()
		self.selectorFrame.setObjectName("selector")
		self.selectorFrame.setStyleSheet(adaptiveStyle("selector",palette = self.res.buttonPanelPalette[0]))
		self.selectorFrame.setFixedSize(rPix(((14/tconNum))*(50+40))*tconNum+1,rPix(35))
		self.selectorFrame.setLayout(selectorHLayout)
		
		## Center Y Axis of selectorFrame
		selectorVLayout = QVBoxLayout()
		selectorVLayout.addStretch(1)
		selectorVLayout.addWidget(self.selectorFrame)
		selectorVLayout.addStretch(1)
		
		
		## Selector Frame (MAIN-14)
		
		topLayout = QHBoxLayout()
		topLayout.addWidget(self.prevStack)
		topLayout.addStretch(1)
		topLayout.addLayout(selectorVLayout)
		topLayout.addStretch(1)
		topLayout.addWidget(self.nextStack)
		topLayout.setContentsMargins(rPix(20),0,rPix(20),0)
		topLayout.setSpacing(rPix(20))
		
		##Selector Frame + Prev and Next Button
		topFrame = QFrame()
		topFrame.setObjectName("noframe")
		topFrame.setStyleSheet(styles["noframe"])
		topFrame.setFixedSize(self.dim[1],rPix(80))
		topFrame.setLayout(topLayout)
		
		
		##Bottom Panel OBJECTS
		reqAssistance = ImageButton("resources/img/buttons/assist",rPix(30),rPix(30),toggle=False,tooltip="<b>Request Assistance</b>")
		reqAssistance.setFixedSize(rPix(30),rPix(30))
		
		manual = ImageButton("resources/img/buttons/manual",rPix(30),rPix(30),toggle=False,tooltip="<b>Open User Manual</b>")
		manual.clicked.connect(self.manualEvt)
		
		self.upload = ImageButton("resources/img/buttons/upload",rPix(30),rPix(30),toggle=True,tooltip="<b>Upload Scores</b>")
		self.upload.clicked.connect(self.uploadScores)
		
		##Semi Rounded Rectangle LAYOUT
		buttonLayout = QHBoxLayout()
		buttonLayout.addWidget(self.upload)
		buttonLayout.addWidget(reqAssistance)
		buttonLayout.addWidget(manual)
		buttonLayout.setContentsMargins(rPix(10),0,rPix(10),0)
		buttonLayout.setSpacing(rPix(20))
		
		self.buttonFrame = QFrame()
		self.buttonFrame.setObjectName("buttonFrame")
		self.buttonFrame.setStyleSheet(adaptiveStyle("buttonFrame",palette = self.res.buttonPanelPalette[0]))
		self.buttonFrame.setFixedSize(rPix(140),rPix(45))
		self.buttonFrame.setLayout(buttonLayout)
		
		##Semi Rounded Rectangle Handler
		
		botLayout = QHBoxLayout()
		botLayout.addStretch(1)
		botLayout.addWidget(self.buttonFrame)
		botLayout.setContentsMargins(rPix(20),0,0,0)
		botLayout.setSpacing(rPix(20))
		
		##Filler Frame for Button Panel
		botFrame = QFrame()
		botFrame.setObjectName("noframe")
		botFrame.setStyleSheet(styles["noframe"])
		botFrame.setFixedSize(self.dim[1],rPix(45))
		botFrame.setLayout(botLayout)
		
		
		##Top Frame + Stack 
		stackLayout = QVBoxLayout(self)
		stackLayout.setContentsMargins(0,0,0,0)
		stackLayout.setSpacing(0)
		stackLayout.addStretch(1)
		stackLayout.addWidget(topFrame)
		stackLayout.addWidget(stackFrame)
		stackLayout.addWidget(botFrame)
		stackLayout.addStretch(1)
		
		##StackFrame
		stackLayoutFrame = QFrame()
		stackLayoutFrame.setObjectName("noframe")
		stackLayoutFrame.setStyleSheet(styles["noframe"])
		stackLayoutFrame.setLayout(stackLayout)
		
		##Mask Layout
		maskHLayout = QHBoxLayout()
		maskHLayout.setContentsMargins(0,0,0,0)
		maskHLayout.setSpacing(0)
		maskHLayout.addStretch(1)
		maskHLayout.addWidget(stackLayoutFrame)
		maskHLayout.addStretch(1)
		
		maskVLayout = QHBoxLayout()
		maskVLayout.setContentsMargins(0,0,0,0)
		maskVLayout.setSpacing(0)
		maskVLayout.addStretch(1)
		maskVLayout.addLayout(maskHLayout)
		maskVLayout.addStretch(1)
		
		##Mask Frame
		mask = QFrame()
		mask.setObjectName("mask")
		mask.setStyleSheet(styles["mask"])
		mask.setLayout(maskVLayout)
		
		## Placeholder Layout
		MainPlaceholderLayout = QHBoxLayout()
		MainPlaceholderLayout.setContentsMargins(0,0,0,0)
		MainPlaceholderLayout.setSpacing(0)
		MainPlaceholderLayout.addWidget(mask)
		
		self.setLayout(MainPlaceholderLayout)
		self.prevStack.setEnabled_(False)
		self.stackSelector[0].setEnabled(False)
		self.showFullScreen()
	def mainStackUI(self): ## Main Stack UI design
		self.mainStack.setFixedSize(rPix(1600),rPix(885))
		_pixmap = QPixmap("resources/img/background.jpg")
		
		mainFrame =ImageFrame()
		mainFrame.setFixedSize(rPix(1600),rPix(885))
		mainFrame.setPixmap(_pixmap, ap = 2)
		lay = QHBoxLayout()
		lay.setContentsMargins(0,0,0,0)
		lay.setSpacing(0)
		lay.addWidget(mainFrame)
		
		self.mainStack.setLayout(lay)
	def manualEvt(self): ## Runs User Manual and hides widget, if manual is closed, the widget is shown
		self.setHidden(True)
		try:
			subprocess.Popen(os.path.join(currentDir(), "resources\\usermanual.docx"),shell=True).wait()
			## Refreshes current image
			try:
				currentStack = self.stack.currentWidget()
				currentStack.imageFrame.setPixmap(currentStack.pixmaps[str(currentStack.conNum)][currentStack.imgNum])
			except: pass
		except Exception as e:
			print("[*] Error, cannot open user manual: " + str(e))
		self.setHidden(False)
	def nextEvt(self):
		if self.stackIndex !=0:
			self.recolorSelector()
		self.stackIndex +=1
		while self.stackIndex in self._magicList:
			self.stackIndex +=1	
		self.stackIndexChanged()
	def prevEvt(self):
		if self.stackIndex !=0:
			self.recolorSelector()
		self.stackIndex -=1
		while self.stackIndex in self._magicList:
			self.stackIndex -=1	
		self.stackIndexChanged()
	def resetStackColor(self):
		for i in self.stackSelector:
			stackSelectorState(i,0)
	def recolorSelector(self):
		if(os.path.isfile(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(self.stackIndex)+".yml"))):
			stackSelectorState(self.stackSelector[self.stackIndex],1)
		else:
			stackSelectorState(self.stackSelector[self.stackIndex],2)
	def stackSelectorEvt(self,index):
		if self.stackIndex !=0:
			self.recolorSelector()
		self.stackIndex = index
		self.stackIndexChanged()
		
	def uploadScores(self):
		for i in range(1,tconNum+1):
			if(os.path.isfile(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(i)+".yml"))):
				pass
			else:
				_html = self.stack.widget(tconNum/2).sheet.page()
				_html.runJavaScript('alert("Missing Scoresheet! '+str(i)+'.yml not found.");')
				return
			
		while not self.isConnected:
			try:
				self.sock.connect((Serv_Data[0],Serv_Data[1]))
				print("Connected")
				self.isConnected = True
				break
				pass
			except Exception as e:
				with open("client.debug.log", "w+") as _flog:
					_flog.write("[*] Error : "+str(e))
				print("Cannot Connect: " +str(e))
				_html = self.stack.widget(tconNum/2).sheet.page()
				_html.runJavaScript('alert("' + str(e) + '");')
				self.terminate = True
				self.close()
				return
				
		x = "-sheetF=?="+str(id)
		self.sock.send(x.encode())
		for i in range(1,tconNum+1):
			_f = open(os.path.join(currentDir(), "resources\\data\\sheets\\"+str(i)+".yml"),"r")
			_istream = _f.read()
			print(_istream)
			x="=?="+str(i)+">?>"
			self.sock.send(x.encode())
			self.sock.send(_istream.encode())
			self.sock.send(">?>-EOF-".encode())	
			_f.close()
		self.sock.send("=?=-EOFT-".encode())	
		_html = self.stack.widget(tconNum/2).sheet.page()
		_html.runJavaScript('alert("Scoresheet uploaded to server.");')
		for i in self.stackSelector:
			i.setEnabled(False)
		self.nextStack.setEnabled_(False)
		self.prevStack.setEnabled_(False)
		self.stack.setCurrentIndex(0)
		self.sock.close()
		
	def stackIndexChanged(self): ## TODO: (x002)
		if self.stackIndex == tconNum: ##Check if index is last, disabling next button
			self.nextStack.setEnabled_(False)
		else:
			self.nextStack.setEnabled_(True)
			
		if self.stackIndex == 0: ##Check if index is first, disabling prev button
			self.prevStack.setEnabled_(False)
		else:
			self.prevStack.setEnabled_(True)
			
		if self.stackIndex == 0: ##Check if index is first, setting palette of adaptive frames to fit Main UI
			self.buttonFrame.setStyleSheet(adaptiveStyle("buttonFrame",palette = self.res.buttonPanelPalette[0]))
			self.selectorFrame.setStyleSheet(adaptiveStyle("selector",palette = self.res.buttonPanelPalette[0]))
		else: ##Setting palette of adaptive frame to match cStack background
			self.selectorFrame.setStyleSheet(adaptiveStyle("selector",palette = self.res.buttonPanelPalette[1][(self.stackIndex-1)%4]))
			self.buttonFrame.setStyleSheet(adaptiveStyle("buttonFrame",palette = self.res.buttonPanelPalette[1][(self.stackIndex-1)%4]))
				
		self.stack.setCurrentIndex(self.stackIndex)
	## Enables every stack selector except current TO:DO (x001)
		for i in self.stackSelector:
			i.setEnabled(True) 
		self.stackSelector[self.stackIndex].setEnabled(False)
		try:
			currentStack = self.stack.currentWidget()
			if self.stackIndex !=0:
				currentStack.activate()	
			
				currentStack.imageFrame.setPixmap(currentStack.pixmaps[str(currentStack.conNum)][currentStack.imgNum])
		except Exception as e:
			print(e)
			
	def centerWidget(self): ##Move widget to center of screen
		_frame = self.frameGeometry()
		_center = app.desktop().availableGeometry().center()
		_frame.moveCenter(_center)
		self.move(_frame.topLeft())
	def closeApp(self): ##Override close event unless Ctrl W
		self.terminate = True
		self.close()
		return
	def closeEvent(self, event): ##Override close event unless Ctrl W
		if not self.terminate:
			event.ignore()
		else:
			event.accept()
	
if __name__ == '__main__':
	resObj = ResourceManager()
	ex = mainWidget(resObj)
	
	sys.exit(app.exec_())
	
# ---------- T O   D O   L I S T -------------
# x002: Disable next/prev buttons when current cStack scores aren't saved yet
# x005: Multithreading support to load images faster
# x006: Open manual and set on top instead of hiding widget
# x007: Sheet flashes on Load
