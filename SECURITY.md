# Security policy

## Reporting a vulnerability

**Please do not report it in public.** Use GitHub's private vulnerability
reporting on this repository: the **Security** tab, then *Report a
vulnerability*. It reaches only the maintainer and does not require
exchanging email addresses. If it is unavailable to you, get in touch through
**[radioterapia.ai](https://radioterapia.ai)** and say only that you have a
security report; the details can then move to a private channel.

**Never attach patient data**, here or anywhere else: no DICOM series, no
RTSTRUCT, no screenshot of a patient image, no log with a patient ID, a UID
or a series path. Describe the problem in words, or reproduce it with the
synthetic phantoms the batteries build.

## What is in scope

The code in this repository: the shell shared by the six apps, the local
server's routes, the installer, the updater and the packager. The findings
that matter most are the ones that expose patient data or let the program act
where it should not:

- Anything that lets another machine, or a web page from another origin,
  reach the local server, which listens only on `127.0.0.1`.
- Anything that sends an image, a structure or a patient identifier off the
  workstation, or puts a patient's folder path in a URL.
- Anything that writes patient data into a folder that syncs to the cloud.
- Anything that makes the installer or the updater accept a package it
  should refuse, or close a process that is not the program's own.

Each of the six apps has its own repository in the same organization; a
finding in an app's code can be reported there or here. The segmentation
models and the third-party libraries are their authors' work: a problem in
one of them belongs with its authors, listed in [NOTICE](NOTICE).

## Not a medical device

Teaching and research material, not a medical device, not validated for
clinical use: a clinically wrong result is a correctness bug, not a
vulnerability, and is welcome through
**[radioterapia.ai](https://radioterapia.ai)**, without patient data.

## Supported versions

The latest release. Single maintainer, no backports.
