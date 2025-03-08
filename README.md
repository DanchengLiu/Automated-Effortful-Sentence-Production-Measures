**README

Calculate the word per minute, stall rate, and revision rat for a folder containing some transcription files.

The input file are considered to be in the same format as the test.cex. It should have a [\+ xx] at the end of any sentence that we wish to compute metrics on, and it should have a timestamp at the end of a sentence.


****Things to note: 

1. file_extension should be set to the correct file extension.

2. folder_to_process should be changed to the input folder containing the files. Please make sure that in the folder, there are no extra files with the target extension other than those whch you wish to compute the metrics on.

3. Both folder_to_process and detailed_folder (if you want detailed output) should be set to an existing directory.


****Example usage

python csv_all.py 
