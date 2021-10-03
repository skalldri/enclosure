# enclosure
A terminal-GUI program written in Python for interacting with hard-disk enclosures.

## Development Status

This project is currently a work-in-progress. Expect large, sweeping updates to the codebase at a moment's notice.

Python isn't my main language: I mostly work in C and C++, so to any hardcore Python programmers reading this code: I'm sorry.

## Overview

This program is intended to make it easier to physically manage hard disks within a large hard disk enclosure, such as the ones commonly found on enterprise-grade server chassis.

Short term goals:
- Provide a console-GUI interface for working with server enclosures
- Enable point-and-click drive identification and status information
- Provide a workflow for users to describe the physical layout of hard drives on their enclosure
- Automatically detect present / empty drive bays
- Control enclosure LED and power status

Long term goals:
- Identify which disks are part of ZFS pools, and provide disk identification based on usage
- Identify ZFS hot-spare drives
- Identify mount-points for drives in the pool
