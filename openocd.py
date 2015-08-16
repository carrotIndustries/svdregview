import telnetlib

class OOCDTelnet:
	def __init__(self, host="localhost", port=4444,timeout=1): 
		self.tel = telnetlib.Telnet(host, port) 
		self.timeout = timeout
		self.read_data()
	
	def close(self): 
		self.tel.close()

	def read_data(self): 
		return self.tel.read_until(b"\r\n\r", self.timeout).decode()

	def command(self, com): 
		self.tel.write(("%s\r\n" % com).encode()) 
		return self.read_data()
		
	def parse_response(self, resp) :
		return int([x for x in resp.split("\n") if len(x)][1].split(":")[1].strip(), 16)
	
	def size_to_char(self, size) :
		if size == 32 :
			return "w"
		elif size == 16 :
			return "h"
		elif size == 8 :
			return "b"
		else :
			raise ValueError
		
	
	def memory_read(self, addr, size=32) :
		#print("readmem")
		return self.parse_response(self.command("md{:s} 0x{:x}".format(self.size_to_char(size), addr)))

	def memory_write(self, addr, value, size=32) :
		#print("writemem")
		self.command("mw{:s} 0x{:x} 0x{:x}".format(self.size_to_char(size), addr, value))

if __name__ == "__main__" :
	tn = OOCDTelnet()
