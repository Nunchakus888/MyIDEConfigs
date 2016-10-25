#-*-coding:utf-8-*- 
import sublime,sublime_plugin
import os,platform,json,logging,subprocess,sys,traceback,shutil 
from xml.etree.ElementTree import ElementTree,Element

curDir = os.path.dirname(os.path.realpath(__file__))

def CleanDir( Dir ):
    if os.path.isdir( Dir ):
        paths = os.listdir( Dir )
        for path in paths:
            filePath = os.path.join( Dir, path )
            if os.path.isfile( filePath ):
                try:
                    os.remove( filePath )
                except os.error:
                    autoRun.exception( "remove %s error." %filePath )
            elif os.path.isdir( filePath ):
                shutil.rmtree(filePath,True)
    return True

class BuildApkCommand(sublime_plugin.WindowCommand):
    """docstring for BuildApkCommand"""
    __curDir=''
    __appId=''
    __cachePath=''
    __cmdLogType='' 
    __fullScreen=False
    __apkLogging=None
    __file_handler=None
    
    def __init__(self,arg):
        self.__curDir=curDir
        self.__apkLogging=logging.getLogger('apk')
        self.__file_handler =logging.FileHandler(os.path.join(self.__curDir,'tmp','apicloud_build.log'))
        self.__apkLogging.setLevel(logging.DEBUG) 
        formatter=logging.Formatter('%(asctime)s %(message)s')
        self.__file_handler.setFormatter(formatter)
        self.__apkLogging.addHandler(self.__file_handler)

    def is_visible(self, dirs): 
        return len(dirs) == 1

    def is_enabled(self, dirs):
        if 0==len(dirs):
            return False
        appFileList=os.listdir(dirs[0])
        if 'config.xml' in appFileList:
            return True
        return False

    def run(self, dirs):
        self.__appId=''
        self.__cachePath=os.path.join(self.__curDir,'tmp')
        self.__fullScreen=False
        self.__apkLogging.info('*'*30+'begin build andriod'+'*'*30)

        try:
            self.buildApk(dirs[0])
            pass
        except:
            self.__apkLogging.info('run: exception happened as below')
            errMsg=traceback.format_exc()
            self.__apkLogging.info(errMsg)
        finally:
            self.__file_handler.close()
            pass

        sublime.status_message(u'build done')
        self.__apkLogging.info('*'*30+'build complete'+'*'*30)

    def checkBasicInfo(self):
        self.__apkLogging.info('checkBasicInfo: current dir is '+self.__curDir)
        self.__apkLogging.info('checkBasicInfo: current platform is '+platform.system().lower())
        if 'darwin' in platform.system().lower():
            if not os.path.exists(os.path.join(self.__curDir,'tools','mac')) or not os.path.isdir(os.path.join(self.__curDir,'tools','mac')):
                self.__apkLogging.info('checkBasicInfo:cannot find tools')
                return -1
        elif 'windows' in platform.system().lower(): 
            if not os.path.exists(os.path.join(self.__curDir,'tools','windows')) or not os.path.isdir(os.path.join(self.__curDir,'tools','windows')):
                self.__apkLogging.info('checkBasicInfo:cannot find tools')
                return -1
        else:
            self.__apkLogging.info('checkBasicInfo: the platform is not supported')
            return -1
        if not os.path.exists(os.path.join(self.__curDir,'appLoader','apicloud-loader','load.apk')):
            self.__apkLogging.info('checkBasicInfo: cannot find appLoader')
            return -1
        if not os.path.exists(os.path.join(self.__curDir,'appLoader','apicloud-loader','load.conf')):
            self.__apkLogging.info('checkBasicInfo: cannot find appLoader')
            return -1
        with open(os.path.join(self.__curDir,'appLoader','apicloud-loader','load.conf')) as f:
            config=json.load(f)
            self.__apkLogging.info('checkBasicInfo: config content is '+str(config))
            if 'cmdLogType' in config:
                self.__cmdLogType=config['cmdLogType']    
        return 0

    def runShellCommand(self, cmd):
        rtnCode=0
        stdout=''
        stderr=''

        if 'darwin' in platform.system().lower():
            p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
            stdoutbyte,stderrbyte=p.communicate()
            stdout=str(stdoutbyte)
            stderr=str(stderrbyte)
            rtnCode=p.returncode

        elif 'windows' in platform.system().lower():
            if 'logFile'==self.__cmdLogType:
                p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
                stdoutbyte,stderrbyte=p.communicate()
                stdout=str(stdoutbyte)
                stderr=str(stderrbyte.decode('GBK'))
                rtnCode=p.returncode
            else:    
                p=subprocess.Popen(cmd,shell=False)
                p.wait()
                rtnCode=p.returncode
        else:
            self.__apkLogging.info('runShellCommand: the platform is not support')
        return (rtnCode,stdout,stderr)  

    def decompileApk(self):
        self.__apkLogging.info('decompileApk:begin decompileApk')

        if 'darwin' in platform.system().lower() :
            apkToolsPath='"'+os.path.join(self.__curDir,'tools','mac','apktool.jar')+'"'
        elif 'windows' in platform.system().lower(): 
            apkToolsPath='"'+os.path.join(self.__curDir,'tools','mac','apktool.jar')+'"'
        else:
            return
        sourceApk='"'+os.path.join(self.__curDir,'appLoader','apicloud-loader','load.apk')+'"' #loader path
        cachePath='"'+os.path.join(self.__curDir,'tmp','android')+'"'
        unzipApk="java -jar " + apkToolsPath+ " d -f -s " + sourceApk + " " + cachePath;
        self.__apkLogging.info('decompileApk: decompileApk cmd is: '+unzipApk)   
        self.runShellCommand(unzipApk)
        pass

    def read_xml(self, in_path):
        tree = ElementTree()
        tree.parse(in_path)
        return tree

    def find_nodes(self, tree, path):
        return tree.findall(path)

    def modifyAndroidManifest(self):
        self.__apkLogging.info('modifyAndroidManifest: begin modifyAndroidManifest')
        androidManifestFile = os.path.join(self.__cachePath,'android','AndroidManifest.xml')
        inputFile=open(androidManifestFile,encoding='utf-8')  
        lines=inputFile.readlines()  
        inputFile.close()
        outputFile =open(androidManifestFile,'w',encoding='utf-8') 
        for line in lines:
            if 'manifest android:versionCode' in line: 
                line='<manifest android:versionCode="6378" android:versionName="1.1.37" package="com.apicloud.'+self.__appId+'"\n'
                outputFile.write(line)
            elif 'com.uzmap.pkg.uzapp.UProvider' in line:
                line='        <provider android:label="udmg" android:name="com.uzmap.pkg.uzapp.UProvider" android:exported="false" android:authorities="'+self.__appId+'.com.apicloud.apploader.ups" />\n'
                outputFile.write(line)            
            elif 'com.uzmap.pkg.uzmodules.uzdownloadmanager.DownloadProvider' in line:
                line='        <provider android:label="udmg" android:name="com.uzmap.pkg.uzmodules.uzdownloadmanager.DownloadProvider" android:process=":remote" android:authorities="'+self.__appId+'.com.apicloud.apploader.uz_downloads" />\n'
                outputFile.write(line)
            else:
                outputFile.write(line)
        outputFile.close()
        pass

    def modifyResAndStyleFile(self):
        self.__apkLogging.info ('modifyResAndStyleFile: begin modifyResAndStyleFile')
        stringsFile = os.path.join(self.__cachePath,'android','res','values','strings.xml')
        inputFile=open(stringsFile,encoding='utf-8')  
        lines=inputFile.readlines()  
        inputFile.close()
        outputFile =open(stringsFile,'w',encoding='utf-8'); 
        for line in lines:
            if '<string name="app_name">' in line: 
                line='    <string name="app_name">'+self.__appName+'</string>\n'
                outputFile.write(line)
            else:
                outputFile.write(line)
        outputFile.close()

        styleFile = os.path.join(self.__cachePath,'android','res','values','styles.xml')
        inputFile=open(styleFile,encoding='utf-8')  
        lines=inputFile.readlines()  
        inputFile.close()
        outputFile =open(styleFile,'w',encoding='utf-8'); 
        for line in lines:
            if '<item name="android:windowFullscreen">' in line: 
                line='        <item name="android:windowFullscreen">'+str(self.__fullScreen)+'</item>\n'
                outputFile.write(line)
            else:
                outputFile.write(line)
        outputFile.close()
        pass

    def copyWidget(self, srcPath):
        self.__apkLogging.info ('copyWidget: begin copyWidget')
        if os.path.exists(os.path.join(self.__cachePath,'android','assets','widget')):
            CleanDir(os.path.join(self.__cachePath,'android','assets','widget'))
            os.rmdir(os.path.join(self.__cachePath,'android','assets','widget'))
        shutil.copytree(srcPath,os.path.join(self.__cachePath,'android','assets','widget'))
        pass

    def packageApk(self, srcPath):
        self.__apkLogging.info ('packageApk: begin packageApk')

        fulldirname=os.path.abspath(srcPath)  
        apkfilename=os.path.basename(fulldirname)+'.apk'
        apkfullfilename=os.path.join(os.path.dirname(fulldirname),apkfilename) 
        if os.path.exists(apkfullfilename):
            return -2

        if 'darwin' in platform.system().lower() :
            apkToolsPath='"'+os.path.join(self.__curDir,'tools','mac','apktool.jar')+'"'
            aaptPath='"'+os.path.join(self.__curDir,'tools','mac','aapt')+'"'
        elif 'windows' in platform.system().lower(): 
            apkToolsPath='"'+os.path.join(self.__curDir,'tools','mac','apktool.jar')+'"'
            aaptPath='"'+os.path.join(self.__curDir,'tools','windows','aapt.exe')+'"'
        else:
            self.__apkLogging.info ('packageApk:platform not supported.')
            return -1

        unsignedApk='"'+os.path.join(self.__cachePath,self.__appId+'.unsigned')+'"'
        unsignedApkCmd='java -jar '+apkToolsPath+' b --aapt  '+ aaptPath + ' "'+os.path.join(self.__cachePath,'android')+'" '+unsignedApk
        self.__apkLogging.info ('packageApk:unsignedApkCmd is: '+unsignedApkCmd)
        (rtnCode,stdout,stderr)=self.runShellCommand(unsignedApkCmd)
        if 'logFile'==self.__cmdLogType or 'darwin' in platform.system().lower():
            outputMsg=stdout+stderr
            self.__apkLogging.info('packageApk: unsignedApkCmd outputMsg is '+outputMsg)   
            if 'Excetpion' in outputMsg:
                return -1            
        
        if 'darwin' in platform.system().lower() :
            toolsPath='"'+os.path.join(self.__curDir,'tools','mac','tools.jar')+'"'
            keyFilePath='"'+os.path.join(self.__curDir,'tools','mac','uzmap.keystore')+'"'
        elif 'windows' in platform.system().lower(): 
            toolsPath='"'+os.path.join(self.__curDir,'tools','mac','tools.jar')+'"'
            keyFilePath='"'+os.path.join(self.__curDir,'tools','mac','uzmap.keystore')+'"'

        signedApk='"'+os.path.join(self.__cachePath,self.__appId+'.signed')+'"'
        signedApkCmd='java -classpath '+ toolsPath+' sun.security.tools.JarSigner -keystore ' + keyFilePath \
        +  ' -storepass '+'123456 -signedjar '  + signedApk +' ' + unsignedApk + ' uzmap.keystore'
        self.__apkLogging.info('packageApk: signedApkCmd is: '+signedApkCmd)
        (rtnCode,stdout,stderr)=self.runShellCommand(signedApkCmd)
        if 'logFile'==self.__cmdLogType or 'darwin' in platform.system().lower():
            outputMsg=stdout+stderr
            self.__apkLogging.info('packageApk: signedApkCmd outputMsg is '+outputMsg)   
        
        if 'darwin' in platform.system().lower() :
            zipAlignPath='"'+os.path.join(self.__curDir,'tools','mac','zipalign')+'"'
        elif 'windows' in platform.system().lower(): 
            zipAlignPath='"'+os.path.join(self.__curDir,'tools','windows','zipalign.exe')+'"'
       
        zipAlignCmd=zipAlignPath+ ' -v 4 '+signedApk+' "'+apkfullfilename+'"'
        self.__apkLogging.info('packageApk: zipAlignCmd is: '+zipAlignCmd)
        (rtnCode,stdout,stderr)=self.runShellCommand(zipAlignCmd)
        if 'logFile'==self.__cmdLogType or 'darwin' in platform.system().lower():
            outputMsg=stdout+stderr
            self.__apkLogging.info('packageApk: signedApkCmd outputMsg is '+outputMsg)  
            if 'succesful' not in outputMsg:
                return -1 
        return 0

    def getWidgetInfo(self, srcPath):
        self.__apkLogging.info('getWidgetInfo: begin getWidgetInfo srcPath is '+srcPath)
        if not os.path.exists(srcPath) or not os.path.isdir(srcPath):
            self.__apkLogging.info('getWidgetInfo:file no exist or not a folder!')
            self.__appId=''
            return 
        appFileList=os.listdir(srcPath)
        if 'config.xml' not in appFileList:
            self.__apkLogging.info('getWidgetInfo: please make sure sync the correct folder!')
            self.__appId=''
            return
        tree=self.read_xml(os.path.join(srcPath,"config.xml"))
        rootNode = tree._root
        self.__appId=rootNode.get('id')
        self.__apkLogging.info ('getWidgetInfo: appId is '+self.__appId)
        nodes=tree.findall('name')
        self.__appName=nodes[0].text
        self.__apkLogging.info('getWidgetInfo: appName is '+self.__appName)
        nodes=tree.findall('preference')
        for i in nodes:
            if 'name' in i.attrib.keys() and 'fullScreen'==i.attrib['name']:
                self.__fullScreen=i.attrib['value']
                self.__apkLogging.info ('getWidgetInfo: fullScreen is '+self.__fullScreen)
                break
        return

    def buildApk(self,path):
        self.__apkLogging.info('buildApk: begin buildApk')
        if -1==self.checkBasicInfo():
            sublime.error_message(u'打包缺少文件')
            return
        self.getWidgetInfo(path)
        self.decompileApk()
        self.modifyAndroidManifest()
        self.modifyResAndStyleFile()
        self.copyWidget(path)
        rtnCode=self.packageApk(path)
        if -1==rtnCode:
            sublime.error_message(u'打包失败')
        elif -2==rtnCode:
            sublime.error_message(u'同名apk包已存在，请删除旧版本包')

        if os.path.exists(os.path.join(self.__cachePath,'android')):
            CleanDir(os.path.join(self.__cachePath,'android'))  
        if os.path.exists(os.path.join(self.__cachePath,self.__appId+'.unsigned')):
            os.remove( os.path.join(self.__cachePath,self.__appId+'.unsigned')) 
        if os.path.exists(os.path.join(self.__cachePath,self.__appId+'.signed')):
            os.remove( os.path.join(self.__cachePath,self.__appId+'.signed')) 
        pass

