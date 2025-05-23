#@ File (label="Input Folder:", style="directory") In_Folder
#@ String (label="New Extension:", default=".tif") New_Extension
#@ String (label="Old Extension (optional):", required=False) Old_Extension
#@ Boolean (label="Include Subfolders?", default=False) Include_Subfolders

import os, re

def main(In_Folder, New_Extension, Old_Extension, Include_Subfolders):
	InFolder = In_Folder.getAbsolutePath()
	if not os.path.exists(InFolder):
		raise FileNotFoundError("Input folder does not exist: " + InFolder)
	
	FilesToDo = []
	if Include_Subfolders:
		for root, dirs, files in os.walk(InFolder):
			for file in files:
				FilesToDo.append(os.path.join(root, file))
	else:
		FilesToDo = [os.path.join(InFolder, f) for f in os.listdir(InFolder) if os.path.isfile(os.path.join(InFolder, f))]

	New_Extension = New_Extension.strip()
	if not New_Extension.startswith("."):
		New_Extension = "." + New_Extension

	if Old_Extension:
		Old_Extension = Old_Extension.strip()
		if Old_Extension.startswith("."):
			Old_Extension = Old_Extension[1:]
		RegexPattern = re.compile(r"\." + Old_Extension + r"$")
	else:
		RegexPattern = re.compile(r"\.[^.]+$")

	RenamedFilepaths = [RegexPattern.sub(New_Extension, Filename) for Filename in FilesToDo]
	for x, OldFile in enumerate(FilesToDo):
		NewFile = RenamedFilepaths[x]
		if OldFile != NewFile:
			try:
				os.rename(OldFile, NewFile)
			except Exception as e:
				print("Error renaming" + OldFile +" to " + NewFile + e)
				continue

if __name__ == "__main__":
	main(In_Folder, New_Extension, Old_Extension, Include_Subfolders)