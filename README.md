# CODI Backup

This project can be used to generate backups from (parts of) your system.
If a file is already stored in an older backup and is unchanged, it will not be included in the next backup to minimize storage useage.
Depending on the configuration you can restore multiple backup points which are merged together depending on the configuration.

---

## Installation

```
wget https://github.com/Codingboy/CODIBackup/releases/download/v0.0.1/CODIBackup.zip
unzip CODIBackup.zip
mv -r CODIBackup ~/
rm CODIBackup.zip
cd ~/CODIBackup
echo '#!/bin/bash' > CODIBackup.sh
echo '' >> CODIBackup.sh
echo "$(pwd)/CODIBackup.py --backup" >> CODIBackup.sh
chmod a+x CODIBackup.py
chmod a+x CODIBackup.sh
chmod a+r config.json
```

Additionaly you need to change the config.json

Optionally if you want to automate backups you can use cron:

Open your crontab by:
```
crontab -e
```
And add the following to make sure backups are generated hourly (or chnage it to your needs)
```
0 * * * * * /home/bla/CODIBackup/CODIBackup.sh
```

---

## Configuration

Here is an example configuration:
```
{
	"minutes":0,
	"hours":24,
	"days":28,
	"weeks":12,
	"months":12,
	"years":0,
	"destination":"/home/bla/backup/",
	"folders":
	[
		"/home/bla/.ssh/",
		"/home/bla/.vimrc",
		"/home/bla/.bashrc",
		"/home/bla/.config/",
		"/home/bla/Documents/",
		"/home/bla/Music/",
		"/home/bla/Pictures/"
	],
	"ignore":
	[
		".git/",
		".build/",
		"__pycache__/",
		"*.sqlite",
		"*.log"
	]
}

```

Assuming you backup hourly this configuartions ensures you have up to 24 hour-backups.
As they get older they will be merged into day-backups.
A day-backup contains **not** contain **all** information from the day-backups.
If you made multiple changes to a file which are stored in different hour-backups, they will be inaccessible after the merge.
Only the newest state will be accessible.
But for sure you can access older bay-backups.
If a day-backup is older than 28 days + 24 hours it is meged into an week-backup which stores all updates within a week.
So on for months and years.
If backups are older than all accumulated times they are merged in a base-backup.
Note: months are considered 28 days and years 28*12 days to ensure good mergeability.
If you specify a folder, it should end with a "/".
Do not use shortcuts like "~/".
If the script is run it might run as root user and therefor might specify a wrong folder.

---

## Useage

In the console this program has three modes of operation:

### Backup

```
./main.py --backup
```

Creates a backup.

### Peek

```
./main.py --peek 2023-04-28T00:00:00
```

In peek mode a list of all included files is printed including the information in which backup the file is stored.

### Recover

```
./main.py --recover 2023-04-28T00:00:00 --all
./main.py --recover 2023-04-28T00:00:00 --selection /home/bla/projects/epubreaderapp/
```

Recovers the system from a backup.
Single files or folders can also be recovered.

**WARNING** All already existing files in the system are overwritten.

---

## Backupstrategy

When using this tool you should specify a different physical storage than you are backing up to minimize risk of dataloss due to storage malfunction.
You can also specify an external storage or even remote which is connected as an sshfs for example but it might be slower.
You can also store the backup files via rsync on a remote storage.
Note that all backup files are needed to restore your data.

---

## Windows Support

This tool was written with Linux in mind.
It should also work under Windows but is 100% untested and I bet you will encounter (fixable) bugs.
If you encounter them, please report them.
Otherwise they will not get fixed.

Here is also a big **WARNING** for an **unfixable** design decision.
This script was mainly written for Linux.
There exists a known problem with the Windows support.
Windows has no root directory but multiple drives like "c:/" and "d:/".
A Ziparchive does not have drives but only folders.
So in Linux in a backup "/home/bla/test.txt" becomes "home/bla/test.txt".
In windows "c:/users/bla/documents/test.txt" becomes "users/bla/documents/test.txt".
And also "d:/users/bla/documents/test.txt" becomes "users/bla/documents/test.txt".
**If a file has the same path in Windows except for the driveletter it will override a file in a backup wich will be unrecoverable.**
This is unlikely but definitive possible depending on your useage.
I could have worked around it but with relatively heavy modifications and treating each OS separately.
I thought the current solution might be ok for most Windows users.

You are warned.

---

## Known Issues

- In Windows files with same path except driveletter override each other and can not be recovered.

---

## Contribution

This work heavyly relies on the work of **yudilevi2** from Github who patched zipfile.py with the support to remove files from a zip archive.
But the patch was never merged into the library.
I include the patched code in this project and hope all are ok with it.
If not, contact me.
[Patched zipfile.py](https://github.com/python/cpython/blob/659eb048cc9cac73c46349eb29845bc5cd630f09/Lib/zipfile.py)

---

## FAQ
---

## TODO

- Merge backup files into a single snapshot if required for an external archive

---