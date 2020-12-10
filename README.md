# herBAR
A barcode renamer for herbarium specimens


	usage: barcode-simple.py [-h] -s SOURCE [-p {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}]
	                         [-b BATCH] [-o [OUTPUT]] [-n] [-c CODE] [-v]
	                         [-j [JPEG_RENAME]]

	optional arguments:
	  -h, --help            show this help message and exit
	  -s SOURCE, --source SOURCE
	                        Path to the directory that contains the images to be
	                        analyzed.
	  -p {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}, --project {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}
	                        Project name for filtering in database
	  -b BATCH, --batch BATCH
	                        Flags written to batch_flags, can be used for
	                        filtering downstream data.
	  -o [OUTPUT], --output [OUTPUT]
	                        Path to the directory where log file is written. By
	                        default (no -o switch used) log will be written to
	                        location of script. If just the -o switch is used, log
	                        is written to directory indicated in source argument.
	                        An absolute or relative path may also be provided.
	  -n, --no_rename       Files will not be renamed, only log file generated.
	  -c CODE, --code CODE  Collection or herbarium code prepended to barcode
	                        values.
	  -v, --verbose         Detailed output for each file processed.
	  -j [JPEG_RENAME], --jpeg_rename [JPEG_RENAME]
	                        String will be added to JPEG file names to prevent
	                        name conflicts downstream.