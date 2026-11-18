# Local Suite 8.26 release build

The build uses the verified [8.25.1 SETUP](https://github.com/drhenriquebraga/local-suite/releases/download/v8.25.1/RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_v8.25.1.zip) as its base. The `members` directory contains the exact new or changed installer files. The manifest names the origin and SHA-256 of every file, including the packaged components and both plugin code seeds.

Run `python rebuild.py <8.25.1-setup.zip> <8.26-setup.zip>`. The script checks the input archive, individual members and the final ZIP. The bundled Windows Python version and zlib version used for the reference build appear in the manifest. For this release, use this recipe to reproduce the public installer from its versioned source.
