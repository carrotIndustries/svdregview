#!/usr/bin/python
from gi.repository import Gtk, GObject
import xml.dom.minidom as dom
import sys
import copy
import operator

from widgets import *
from openocd import *

class Peripheral :
	def __init__(self, name, description, group, base_address) :
		self.__dict__.update({(k,v) for k,v in locals().items() if k != "self"})
		self.registers = {}
	
	def append_register(self, reg) :
		reg.peripheral = self
		self.registers[reg.name] = reg
	
	def copy(self) :
		return copy.deepcopy(self)
		
	def __repr__(self) :
		return "Peripheral "+self.name+"@"+hex(self.base_address)

class Register :
	def __init__(self, name, display_name, description, address_offset, size, readable, writable, reset_value) :
		self.__dict__.update({(k,v) for k,v in locals().items() if k != "self"})
		self.fields = {}
		self.cbs = []
		self._auto = False
		self._value = reset_value
	
	def bind(self, cb) :
		self.cbs.append(cb)
	
	def append_field(self, field) :
		field.register = self
		self.fields[field.name] = field
	
	def trigger(self) :
		for cb in self.cbs :
			#print("calling", cb, self._value)
			cb(self._value)
		for field in self.fields.values() :
			for cb in field.cbs :
				cb(field.value)
				
	def read(self) :
		self.value = self.peripheral.connection.memory_read(self.peripheral.base_address+self.address_offset, size=self.size)
		self.trigger()
		
	def write(self) :
		self.peripheral.connection.memory_write(self.peripheral.base_address+self.address_offset, self.value, size=self.size)
	
	@property
	def auto(self) :
		return self._auto
		
	@auto.setter
	def auto(self, v) :
		self._auto = v
		if self._auto :
			self.write()
			self.read()
		
	
	@property
	def value(self) :
		return self._value
	
	@value.setter
	def value(self, v) :
		print("setting", self.name, v)
		if v<0 :
			traceback.print_stack()
			v=0
		print("setting", self.name, v)
		if v != self._value :
			print("really setting", self.name, v)
			self._value = v
			self.trigger()
			if self.auto :
				self.write()
				self.read()
			
class RegisterField :
	def __init__(self, name, description, offset, width) :
		self.__dict__.update({(k,v) for k,v in locals().items() if k != "self"})
		self._value = 0
		self.cbs = []
	
	def bind(self, cb) :
		self.cbs.append(cb)
	
	
	@property
	def value(self) :
		return (self.register.value>>self.offset)&(2**self.width-1)
	
	@value.setter
	def value(self, vn) :
		v = self.register.value
		v &= ~((2**self.width-1)<<self.offset)
		v |= vn<<self.offset
		self.register.value = v

xml=dom.parse(sys.argv[1])
device = xml.getElementsByTagName("device")[0]
peripheralsNode = device.getElementsByTagName("peripherals")[0]
peripherals = {}


for peripheral in  [node for node in peripheralsNode.getElementsByTagName("peripheral") if node.parentNode==peripheralsNode] :
	if peripheral.getAttribute("derivedFrom") == "" :
		name         = [node for node in peripheral.childNodes if node.nodeName=="name"][0].firstChild.nodeValue
		description  = " ".join([node for node in peripheral.childNodes if node.nodeName=="description"][0].firstChild.nodeValue.split())
		try :
			group        = [node for node in peripheral.childNodes if node.nodeName=="group"][0].firstChild.nodeValue
		except IndexError :
			group = ""
		base_address = int([node for node in peripheral.childNodes if node.nodeName=="baseAddress"][0].firstChild.nodeValue, 0)
		#print(name, description, group, base_address)
		p = Peripheral(name, description, group, base_address)
		peripherals[p.name] = p
		for register in [node for node in peripheral.getElementsByTagName("registers")[0].childNodes if node.nodeName=="register"] :
			name         = [node for node in register.childNodes if node.nodeName=="name"][0].firstChild.nodeValue
			try :
				display_name = [node for node in register.childNodes if node.nodeName=="display_name"][0].firstChild.nodeValue
			except IndexError :
				display_name = name
			description = " ".join([node for node in register.childNodes if node.nodeName=="description"][0].firstChild.nodeValue.split())
			address_offset = int([node for node in register.childNodes if node.nodeName=="addressOffset"][0].firstChild.nodeValue, 0)
			size = int([node for node in register.childNodes if node.nodeName=="size"][0].firstChild.nodeValue, 0)
			try :
				reset_value = int([node for node in register.childNodes if node.nodeName=="resetValue"][0].firstChild.nodeValue, 0)
			except (IndexError, ValueError) :
				reset_value = 0
			try :
				readable = "read" in [node for node in register.childNodes if node.nodeName=="access"][0].firstChild.nodeValue
				writable = "write" in [node for node in register.childNodes if node.nodeName=="access"][0].firstChild.nodeValue
			except IndexError :
				readable = True
				writable = True
			r=Register(name, display_name, description, address_offset, size, readable, writable, reset_value)
			p.append_register(r)
			for field in [node for node in register.getElementsByTagName("fields")[0].childNodes if node.nodeName=="field"] :
				name         = [node for node in field.childNodes if node.nodeName=="name"][0].firstChild.nodeValue
				description         = " ".join([node for node in field.childNodes if node.nodeName=="description"][0].firstChild.nodeValue.split())
				offset         = int([node for node in field.childNodes if node.nodeName=="bitOffset"][0].firstChild.nodeValue, 0)
				width         = int([node for node in field.childNodes if node.nodeName=="bitWidth"][0].firstChild.nodeValue, 0)
				f=RegisterField(name, description, offset, width)
				r.append_field(f)
			#r.reset()
		
	else :
		derived = peripheral.getAttribute("derivedFrom")
		p = peripherals[derived].copy()
		p.name = [node for node in peripheral.childNodes if node.nodeName=="name"][0].firstChild.nodeValue
		p.base_address = int([node for node in peripheral.childNodes if node.nodeName=="baseAddress"][0].firstChild.nodeValue, 0)
		peripherals[p.name] = p



builder = Gtk.Builder()
builder.add_from_file("svd.glade")

window = builder.get_object("window1")
window.show_all()

class Handler :	
	def quit(self, widget) :
		Gtk.main_quit()

builder.connect_signals(Handler())


peripheralwidgets = []

connection = OOCDTelnet()

for peripheral in peripherals.values() :
	peripheral.connection=connection


box = builder.get_object("box1")
for peripheral in sorted(peripherals.values(), key=operator.attrgetter("name")) :
	peripheralwidget = PeripheralWidget(peripheral)
	peripheralwidgets.append(peripheralwidget)
	

	
		
		
	box.pack_start(peripheralwidget, True, True, 0)
box.show_all()

Gtk.main()

