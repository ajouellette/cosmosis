import ctypes as ct
from . import lib
from .errors import BlockError
from . import errors
import numpy as np

class Block(object):
	GET=0
	PUT=1
	REPLACE=2
	def __init__(self, ptr=None, own=None):
		self.owns=own
		if ptr is None:
			ptr = lib.make_c_datablock()
			self.owns=True
		if own is not None:
			self.owns=own
		self._ptr = ptr
	#TODO: add destructor.  destroy block if owned

	@staticmethod
	def python_to_c_complex(value):
		if isinstance(value, lib.c_complex):
			return value
		elif isinstance(value, complex):
			return lib.c_complex(value.real,value.imag)
		elif isinstance(value, tuple):
			return lib.c_complex(value[0],value[1])
		else:
			return lib.c_complex(value, 0.0)

	@staticmethod
	def python_to_1d_c_array(value, c_type):
		value = np.array(value, dtype=np.intc)
		#This function is for 1D arrays only
		assert value.ndim==1
		#check strides same as itemsize.
		#This may be false if e.g. the object
		#was made by looking at a slice through
		#a matrix.
		if value.itemsize != value.strides[0]:
			#If so we need to copy the data to create
			#a new object with sensible strides
			value = value.copy()
		assert value.itemsize==value.strides[0]
		#Now return pointer to start of the data
		array = np.ctypeslib.as_ctypes(value)
		array_size = value.size
		#OK, here's the difficult part.
		# We have to return the value, as well as the
		# array we have converted it to.
		# That's because the array object
		# does not maintain a pointer to the value,
		# so it is garbage collected if we don't
		# and then the array just contains junk memory
		return value, array, array_size



	def get_int(self, section, name):
		r = ct.c_int()
		status = lib.c_datablock_get_int(self._ptr,section,name,r)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)
		return r.value

	def get_double(self, section, name):
		r = ct.c_double()
		status = lib.c_datablock_get_double(self._ptr,section,name,r)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)
		return r.value

	def get_complex(self, section, name):
		r = lib.c_complex()
		status = lib.c_datablock_get_complex(self._ptr,section,name,r)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)
		return r.real+1j*r.imag

	def get_string(self, section, name):
		r = lib.c_str()
		status = lib.c_datablock_get_string(self._ptr,section,name,r)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)
		return str(r.value)

	def get_int_array_1d(self, section, name):
		n = lib.c_datablock_get_array_length(self._ptr, section, name)
		r = np.zeros(n, dtype=np.intc)
		arr = np.ctypeslib.as_ctypes(r)
		sz = lib.c_int()
		status = lib.c_datablock_get_int_array_1d_preallocated(self._ptr, section, name, arr, ct.byref(sz), n)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)
		return r

	def put_int(self, section, name, value):
		status = lib.c_datablock_put_int(self._ptr,section,name,int(value))
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def put_double(self, section, name, value):
		status = lib.c_datablock_put_double(self._ptr,section,name,float(value))
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def put_complex(self, section, name, value):
		value=self.python_to_c_complex(value)
		status = lib.c_datablock_put_complex(self._ptr,section,name,value)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def put_string(self, section, name, value):
		status = lib.c_datablock_put_string(self._ptr,section,name,str(value))
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def put_int_array_1d(self, section, name, value):
		value_ref, value,n=self.python_to_1d_c_array(value, ct.c_int)
		status = lib.c_datablock_put_int_array_1d(self._ptr, section, name, value, n)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def _method_for_value(self, value, method_type):
		T = type(value)
		method={ int:(self.get_int,self.put_int,self.replace_int),
		         float:(self.get_double,self.put_double,self.replace_double),
		         complex:(self.get_complex,self.put_complex,self.replace_complex),
		         str:(self.get_string,self.put_string,self.replace_string)
		         }.get(T)
		if method:
			return method[method_type]
		if hasattr(value,'__len__'):
			array = np.array(value)
			method = {
				(1,'i'):(self.get_int_array_1d,self.put_int_array_1d,self.replace_int_array_1d),
				#These are not implemented yet
				# (2,'i'):(self.get_int_array_2d,self.put_int_array_1d,self.replace_int_array_1d),
				# (1,'f'):(self.get_double_array_1d,self.put_double_array_1d,self.replace_double_array_1d),
				# (2,'f'):(self.get_double_array_2d,self.put_double_array_1d,self.replace_double_array_1d),
				# (1,'c'):(self.get_complex_array_1d,self.put_complex_array_1d,self.replace_complex_array_1d),
				# (2,'c'):(self.get_complex_array_2d,self.put_complex_array_1d,self.replace_complex_array_1d),
			}.get((array.ndim,array.dtype.kind))
			if method:
				return method[method_type]
		raise ValueError("I do not know how to handle this type %r %r"%(value,type(value)))


	def put(self, section, name, value):
		method = self._method_for_value(value,self.PUT)
		method(section, name, value)

	def replace(self, section, name, value):
		method = self._method_for_value(value,self.REPLACE)
		method(section, name, value)


	def replace_int(self, section, name, value):
		status = lib.c_datablock_replace_int(self._ptr,section,name,value)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def replace_double(self, section, name, value):
		r = ct.c_double()
		status = lib.c_datablock_replace_double(self._ptr,section,name,value)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def replace_complex(self, section, name, value):
		value=self.python_to_c_complex(value)
		status = lib.c_datablock_replace_complex(self._ptr,section,name,value)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def replace_string(self, section, name, value):
		status = lib.c_datablock_replace_string(self._ptr,section,name,str(value))
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)

	def replace_int_array_1d(self, section, name, value):
		value_ref, value,n=self.python_to_1d_c_array(value, ct.c_int)
		status = lib.c_datablock_replace_int_array_1d(self._ptr, section, name, value, n)
		if status!=0:
			raise BlockError.exception_for_status(status, section, name)