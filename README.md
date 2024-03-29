# Basic integration of barcode commands, UIC PNP machines, Xero invoicing and conveyors to inventree
This stuff is useful to us but comes with totally no support.

This is a work in progress and is pretty arse. The send_pnp_log.py runs on a pair of Universal Genesis PNP machines running Windows 2000. It needs the most recent version of Python3 you can get to run on Win2k.    

The xero invoice bit takes done sales orders in inventree, marks them as invoices and generates draft invoices in Xero. 

The other stuff is mostly to make it easy to automate build orders and putting units onto sales orders. Our goal is to never need to enter data in inventree, or use any of the inventree build order interface apart from if we want to look at info. All changes to stock level and unit building should be from machines or barcodes. 

