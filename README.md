# BoringXplorer

**BoringXplorer** is a Python library designed for geotechnical engineers and
researchers who need to automate the extraction of data from BBS 137 rev. 8-99
Soil Boring Log documents. It processes all pages in a PDF, identifies those in
the correct format, and exports the extracted data into three CSV files
corresponding to document headers, lithology sections, and blow counts.


## Installation

**BoringXplorer** was developed and tested with **Python 3.11.9**. So it is
recommended to use that version or newer.

### Steps for installation

#### 1. Install Python
You can find the recommended version and others at the Python website:
**https://www.python.org/downloads/**

#### 2. Clone the repository
```bash
git clone https://github.com/noahBax/IDOT-BoringXplorer.git
```
**or** download and unpack a ZIP file

#### 3. Install the required dependencies
```bash
python -m pip install -r requirements.txt
```
If you are on a **Windows** machine, you can just run the **setup.bat** file

## Usage

To run the program, use the following command in a terminal running inside of
the same directory the "config.ini" file is in
```bash
python index.py
```
If you are on a **Windows** machine, you can just start the **run.bat** file

## Configuration
You can customize the behavior of the program via the "config.ini" file.

### 1. Where to look for PDFs
Change the `PDFsParentFolder` option to the address of the folder containing all
the PDFs you want to analyze. The PDFs don't all need to be directly under the
path you provide. The program recursively looks through all files underneath the
parent. For example, a parent folder containing a bunch of smaller folders where
each has reports from a single county will work just fine.

### 2. Put date strings into output files
By default, to prevent you accidentally overwriting past results, the
`UseDateInOutputFileNames` field is set to 'yes'. This will add a small
timestamp to the start of each of the output files. If you disable this, it will
just output **"headers_tabulated.csv"**, **"blowcounts_tabulated.csv"**, and
**"lithology_formations_tabulated.csv"**

### 3. Adjust the resources the program uses
There are two fields to adjust resource usage: `LowMemoryMode` and `UseMultiThreading`.

Enabling `UseMultiThreading` speeds up the program by splitting up the work
among multiple processes. This can take up more resources, but will disable
itself if your machine doesn't support it. It is enabled by default.

Enabling `LowMemoryMode` attempts to curb the maximum amount of RAM that the
program uses at any given moment. `UseMultiThreading` is disabled automatically
if this option is enabled. While the program will attempt to use less RAM, this
isn't always guaranteed due to the nature of some of the documents it's scanning
being obnoxiously long

For logging purposes if you want to debug, enable `WriteAllLogsToFiles`. This is
disabled by default. Enabling this can generate a LOT of log files so use
carefully.

## Some Things to be Aware of
The program does handle pretty much all of the cases, but doing optical
character recognition and document orientation recognition add some element of
randomness every time this program runs. The output from run to run will mostly
resemble each other, but there will be differences between them.

## Technologies
This program largely relies on the
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) project for recognizing
text and relies on [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for interacting
with PDF files.