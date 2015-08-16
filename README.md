svdregview
==========

svdregview is a small Gtk+ utility written in python3 to access peripheral registers of ARM 
MCUs. It seeks to provide functionality similar to the 
KEIL™ System Viewer.

#How it works
svdregview leverages the CMSIS System View Description file format to obtain 
the names and addresses of peripheral registers. SVD files for various 
MCUs can be obtained from [cmis.arm.com](http://cmsis.arm.com/) (after registration). 
The MCU is accessed via OpenOCD's telnet interface. 

#How do I use
 - clone this repo
 - get SVD file for your MCU (see above)
 - start openocd
 - ./svd.py &lt;your-svd-file&gt;

#How it looks like
![screenshot](screenshot.png?raw=true)

#Dependencies
 - python3
 - openocd
 - Gtk+ 3
 - python gobject introspection

#Bugs / missing features
 - no support for enumerated register fields (ST, please add enumerations to your SVD files and headers. Atmel does)
 - can't close openocd connection (have to exit svdregview before programming MCU)
 - only tested with STM32F4 series MCUs
