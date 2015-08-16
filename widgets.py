from gi.repository import Gtk, GObject
import operator
import traceback
import re

def userevent(f) :
	def inner(*args, **kwargs) :
		if Gtk.get_current_event() is not None :
			f(*args, **kwargs)
	return inner


class PeripheralWidget (Gtk.Expander):
	def __init__(self, peripheral) :
		self.peripheral = peripheral
		Gtk.Expander.__init__(self)
		self.set_label(peripheral.name + " (" + peripheral.description+")")
		self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.box.set_margin_start(16)
		self.add(self.box)
		self.connect("activate", self.expanded_handler)
		self.populated = False
		self.registers = []
	
	def expanded_handler(self, w) :
		print("expand", self.get_expanded(), self.populated)
		if not self.populated :
			self.populated = True
			for register in sorted(self.peripheral.registers.values(), key=operator.attrgetter("name")) :
				regwidget = RegisterWidget(register)
				self.append_register(regwidget)
				for field in reversed(sorted(register.fields.values(), key=operator.attrgetter("offset"))) :
					fieldwidget = RegisterFieldWidget(field)
					regwidget.append_field(fieldwidget)
				register.trigger()
			
	def append_register(self, reg) :
		self.registers.append(reg)
		self.box.pack_start(reg, True, True, 0)
		reg.show_all()


class ComboEntry (Gtk.Box) :
	
	__gsignals__ = {
		"value-changed":(GObject.SIGNAL_RUN_FIRST , GObject.TYPE_NONE, (GObject.TYPE_UINT, )),
	}
	
	def __init__(self, lo, hi) :
		Gtk.Box.__init__(self)
		self.set_spacing(4)
		self.hexentry = Gtk.SpinButton.new_with_range(lo, hi, 1)
		self.hexentry.set_numeric(False)
		self.hexentry.connect("value-changed", self.decentry_handler)
		self.hexentry.connect("output", self.hexentry_output)
		self.pack_start(self.hexentry, True, True, 0)
		
		self.decentry = Gtk.SpinButton.new_with_range(lo, hi, 1)
		self.pack_start(self.decentry, True, True, 0)
		self.decentry.connect("value-changed", self.decentry_handler)
		
	def set_value(self, v) :
		self.decentry.set_value(v)
		self.hexentry.set_value(v)
		self.emit("value-changed", int(self.decentry.get_value()))
	
	def get_value(self) :
		return int(self.decentry.get_value())
	
	def decentry_handler(self, w) :
		self.set_value(w.get_value())
	
	def hexentry_output(self, w) :
		v = int(w.get_adjustment().get_value())
		w.set_text(hex(v))
		#print("sethex", self, v)
		#traceback.print_stack()
		return True


class RegisterWidget (Gtk.Expander):
	def __init__(self, register) :
		self.register = register
		
		Gtk.Expander.__init__(self)
		self.connect("activate", self.expanded_handler)
		self.set_label(register.name)
		self.outerbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
		self.outerbox.set_border_width(8)
		self.box = Gtk.FlowBox()
		self.box.set_selection_mode(Gtk.SelectionMode.NONE)
		self.box.set_max_children_per_line(8)
		self.outerbox.set_margin_start(16)
		
		self.bbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
		self.bbox.set_layout(Gtk.ButtonBoxStyle.START)
		self.bbox.set_spacing(16)
		
		self.writebutton = Gtk.Button.new_from_icon_name("gtk-apply", Gtk.IconSize.BUTTON)
		self.writebutton.connect("clicked", self.write_clicked)
		self.writebutton.set_label("Write")
		self.bbox.add(self.writebutton)
		
		self.readbutton = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
		self.readbutton.connect("clicked", self.read_clicked)
		self.readbutton.set_label("Read")
		self.bbox.add(self.readbutton)
		
		self.autobox = Gtk.Box(spacing=4)
		self.autoswitch = Gtk.Switch()
		self.autoswitch.connect("notify::active", self.auto_toggled)
		self.autobox.pack_start(self.autoswitch, False, False,0)
		self.autolabel = Gtk.Label("Auto write")
		self.autobox.pack_start(self.autolabel, False, False,0)
		self.bbox.add(self.autobox)
		
		
		self.outerbox.pack_start(self.bbox, True, True, 0)
		
		self.outerbox.pack_start(self.box, True, True, 0)
		
		self.comboentry = ComboEntry(0, (2**32)-1)
		self.comboentry.set_value(self.register.value)
		self.comboentry.connect("value-changed", self.comboentry_handler)
		self.outerbox.pack_start(self.comboentry, True, True, 0)
		self.register.bind(self.comboentry.set_value)
		self.add(self.outerbox)
		self.fields = []
	
	def expanded_handler(self, w) :
		pass
		self.register.read()
	
	def auto_toggled(self, w, v) :
		self.register.auto = w.get_active()
	
	def write_clicked(self, w) :
		self.register.write()
		self.register.read()
		
	def read_clicked(self, w) :
		self.register.read()
	
	def comboentry_handler(self, w, v) :
		self.register.value = v
	
	def append_field(self, field) :
		self.fields.append(field)
		self.box.insert(field, -1)
		field.show_all()
	

class RegisterFieldWidget (Gtk.Frame) :
	def __init__(self, field) :
		self.field = field
		self.field.bind(self.set_value)
		Gtk.Frame.__init__(self, label="[{:d}:{:d}] {:s}".format(field.offset+field.width-1, field.offset, field.name))
		self.set_shadow_type(Gtk.ShadowType.IN)
		self.outerbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
		self.outerbox.set_border_width(4)
		self.add(self.outerbox)
		self.box = Gtk.Box()
		self.last_value = None
		self.outerbox.pack_start(self.box, True, True, 0)
		if self.field.width > 1:
			self.comboentry = ComboEntry(0, (2**field.width)-1)
			self.comboentry.set_value(self.field.value)
			self.outerbox.pack_start(self.comboentry, True, True, 0)
			
			self.comboentry.connect("value-changed", self.comboentry_handler)
			
		else :
			self.comboentry = None
		self.bits = {}
		for i in reversed(range(self.field.width)) :
			checkbutton = Gtk.CheckButton(label=str(i))
			checkbutton.set_active(self.field.value&(1<<i))
			checkbutton.connect("toggled", self.checkbutton_handler)
			self.bits[i] = checkbutton
			self.box.pack_start(checkbutton, True, True, 0)
	

	
	def comboentry_handler(self, w,v ) :
		self.set_value(w.get_value())
	
	def hexentry_output(self, w) :
		v = int(w.get_adjustment().get_value())
		w.set_text(hex(v))
		return True
	
	@userevent
	def checkbutton_handler(self, w) :
		if Gtk.get_event_widget(Gtk.get_current_event()) != w :
			return
		print("cbh")
		va=0
		for k,v in self.bits.items() :
			if v.get_active() :
				va |= (1<<k)
		self.set_value(va)
	
	def set_value(self, v) :
		if v == self.last_value :
			return
		self.last_value = v
		v=int(v)
		if v<0 : 
			v=0
		elif v>=2**(self.field.width) :
			v=2**(self.field.width)-1
		for i in range(0, self.field.width) :
			self.bits[i].set_active(v&(1<<i))
		if self.comboentry is not None :
			self.comboentry.set_value(v)
		self.field.value = v
		
