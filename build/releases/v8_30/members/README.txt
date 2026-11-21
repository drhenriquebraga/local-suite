LOCAL SUITE 8.30 | 21/11/2026

Extraia o ZIP inteiro e abra START_HERE_TO_INSTALL_LOCAL_SUITE.cmd.
Em uma estação com a Suite instalada, escolha Instalar / Atualizar app nesta máquina.
O instalador exige bundle 8.30 ou superior. As configurações e personalizações da estação são preservadas. A distribuição de avaliação do ROCardS destina-se à pesquisa não comercial.
O código do NEURO RT e do LUNG RT acompanha esta versão. Os pesos opcionais continuam disponíveis pelo instalador e pelas Configurações.

LOCAL_SUITE v8.30 - INSTALLER

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
     Machine with internet: build a        downloads selected tools, makes a .zip
     package to take to the offline
     machine
     Uninstall

Every option that swaps the code closes the app first, if it is open, and says
so in the log.

Installing everything and building a package need internet. Installing from a
package you brought needs none - it only opens the file someone else prepared.
Updating uses the internet when there is some, and the log says each decision
it took.

THE PACKAGE IS ABOUT 20 GB, with all optional tools selected, and preparing it
needs about 41 GB free on disk. It is not inside this .zip on purpose:
that way you build the package with the versions of the day, on your own
machine, and you know exactly what is in it. The same number is in
programa/PACKAGE_SIZE.txt.

This suite is for teaching and research. Before downloading, review each
tool's purpose, authors, code and weight licences, and original sources.
The ROCardS authors restrict use to non-commercial research (CC BY-NC 4.0).
For the JHU pelvic model, MIT covers the code. The checkpoint release does
not state a separate weight licence. See the authors' terms:
  https://github.com/AIM-Harvard/ROCardS#license
  https://github.com/JHU-MICA/TwoStepMalePelvicCTSeg/releases/tag/models

Optional tools are included according to your selection. The destination
workstation requires its own operator consent before installing or updating.

If the preparer stops with an error, its log is kept in
%LOCALAPPDATA%\RadioterapiaAI\logs - the error screen says which file.

This is study and research material. It is NOT a medical device and it is not
validated for clinical use. Every structure comes out as an UNAPPROVED
SUGGESTION; reviewing and approving remains a medical act, in the planning
system.

The interface is available in twelve languages and opens in English. The Terms
of Use and the licence texts are authoritative in their original language.
