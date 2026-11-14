; İsteğe bağlı Inno Setup kurulum betiği. Önce PyInstaller ile dist\OptikSinav klasörü üretilmeli.
; Derleme: iscc /DSurum=0.1.0 paketleme\kurulum.iss
#ifndef Surum
  #define Surum "0.1.0"
#endif
[Setup]
AppId={{6E0C1C1E-5B2A-4F6D-9C51-0B7E0F5A1D21}
AppName=Optik Sınav Değerlendirme
AppVersion={#Surum}
AppPublisher=Ali Osman Öztop
DefaultDirName={autopf}\OptikSinav
DefaultGroupName=Optik Sınav
OutputDir=..\dist
OutputBaseFilename=OptikSinav-{#Surum}-windows-kurulum
SetupIconFile=..\assets\simge.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Files]
Source: "..\dist\OptikSinav\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Optik Sınav"; Filename: "{app}\OptikSinav.exe"
Name: "{autodesktop}\Optik Sınav"; Filename: "{app}\OptikSinav.exe"; Tasks: masaustu

[Tasks]
Name: "masaustu"; Description: "Masaüstüne kısayol oluştur"

[Registry]
Root: HKCU; Subkey: "Software\Classes\.osd"; ValueType: string; ValueData: "OptikSinav.Proje"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\OptikSinav.Proje\shell\open\command"; ValueType: string; ValueData: """{app}\OptikSinav.exe"" ""%1"""; Flags: uninsdeletekey
