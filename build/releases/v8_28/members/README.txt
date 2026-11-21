LOCAL SUITE 8.28 | 20/11/2026

Extraia o ZIP inteiro e abra START_HERE_TO_INSTALL_LOCAL_SUITE.cmd.
Em uma estação com a Suite instalada, escolha Instalar / Atualizar app nesta máquina.
O instalador verifica a compatibilidade e reaproveita o Python e os pesos existentes.
O código do NEURO RT e do LUNG RT acompanha esta versão. Os pesos opcionais continuam disponíveis pelo instalador e pelas Configurações.

LOCAL_SUITE v8.28 - INSTALLER

This file is NOT the program: it is the installer for it.

  1. Extract this whole .zip into a folder.
  2. Double-click START_HERE_TO_INSTALL_LOCAL_SUITE.cmd, from inside the extracted folder.
  3. On the first screen, choose what to do:

     Install / Update app on this machine   the big button: it checks
                                           whether the program is already
                                           here. If not, it installs
                                           everything straight into the
                                           final folder, in one step (no
                                           .zip). If it is, it decides by
                                           itself: a newer installer in the
                                           release is downloaded, checked
                                           and used; same requirements,
                                           code only, no internet;
                                           otherwise everything, online, or
                                           the full .zip you brought -
                                           without one, it cancels
     Offline machine: install from a       installs the .zip you brought
     package I brought
     Machine with internet: build a        downloads everything, makes a .zip
     package to take to the offline
     machine
     Uninstall

Every option that swaps the code closes the app first, if it is open, and says
so in the log.

Installing everything and building a package need internet. Installing from a
package you brought needs none - it only opens the file someone else prepared.
Updating uses the internet when there is some, and the log says each decision
it took.

THE PACKAGE IS ABOUT 20 GB, always the complete one, and preparing it
needs about 41 GB free on disk. It is not inside this .zip on purpose:
that way you build the package with the versions of the day, on your own
machine, and you know exactly what is in it. The same number is in
programa/PACKAGE_SIZE.txt.

The component licences are shown before any download, and none of them starts
without acceptance. None of them is non-commercial: every model allows
commercial use, and the NOTICE file says which licence is whose.

If the preparer stops with an error, its log is kept in
%LOCALAPPDATA%\RadioterapiaAI\logs - the error screen says which file.

This is study and research material. It is NOT a medical device and it is not
validated for clinical use. Every structure comes out as an UNAPPROVED
SUGGESTION; reviewing and approving remains a medical act, in the planning
system.

The interface is available in twelve languages and opens in English. The Terms
of Use and the licence texts are authoritative in their original language.
