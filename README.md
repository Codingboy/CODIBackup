# CODI Backup

This project can be used to generate backups from (parts of) you system.
If a file is already stored in an older backup and is unchanged, it will not be included in the next backup to minimize storage useage.
Depending on the configuration you can restore multiple backup points which are merged together depending on the configuration.

---

## Installation

Simply copy the project to your system, navigate to it in the console and execute main.py
```
wget 
unp
cd 
python3 main.py --backup
```

---

## Configuration

Here is an example configuration:
```
{
	"days":21,
	"weeks":6,
	"months":3,
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
		".build/"
	]
}
```
Assuming you backup daily this configuartions ensures all backups are kept for 21 days. Even if you do hundres of backups a day.
If a backup is older than 21 days it is meged into an older backup which stores all updates within a week. Note: when backups get merged the individual backup can never be restored because they are modified. So on for months and years. If backups are older than all accumulated times they are merged in a base backup.
Note months are considered 28 days and years 28*12 days to ensure good mergeability.

---

## Useage
---

## FAQ
---

## TODO
- support for filepatterns in ignore
- option to compress backups
- windows support
---