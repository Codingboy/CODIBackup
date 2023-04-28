# CODI Backup

This project can be used to generate backups from (parts of) you system.
If a file is already stored in an older backup and is unchanged, it will not be included in the next backup to minimize storage useage.
Depending on the configuration you can restore multiple backup points which are merged together depending on the configuration.

---

## Installation

Open your crontab by:
```
crontab -e
```
And add the following to make sure backups are generated hourly (or chnage it to your needs)
```
0 * * * * * /home/bla/projects/backup/CODIBackup.sh
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
./main.py --recover 2023-04-28T00:00:00
```

Recovers the system from a backup.

**WARNING** All already existing files in the system are overwritten.

---

## FAQ
---

## TODO
- recover single files/folders
- windows support
---