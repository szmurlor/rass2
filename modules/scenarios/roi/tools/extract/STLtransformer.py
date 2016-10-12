import re
import sys

help= '''
A simple STL transformer.
Usage: %s STL-file
'''

def STLbbox( filename ):
	ifile = open(filename, "r")

	splitter = re.compile( '\\s+' )

	bbox = [ 1e6, 1e6, 1e6, -1e6, -1e6, -1e6 ]

	for l in ifile:
		line = l.lower()
		if line.find( 'vertex' ) >= 0:
			tokens= splitter.split( line )
			while tokens[0] == '':
				tokens.pop(0)
			if tokens[0] == 'vertex':
				x= map( lambda x : float(x), tokens[1:4] )
				for i in range(len(x)):
					if bbox[i] > x[i]:
						bbox[i] = x[i]
					if bbox[i+3] < x[i]:
						bbox[i+3] = x[i]
	ifile.close()
	return bbox

def STLtranslate( filename, dx, dy, dz ):
	ifile = open(filename, "r")

	splitter = re.compile( '\\s+' )

	bbox = [ 1e6, 1e6, 1e6, -1e6, -1e6, -1e6 ]

	for orgline in ifile:
		line = orgline.lower()
		if line.find( 'vertex' ) >= 0:
			tokens= splitter.split( line )
			while tokens[0] == '':
				tokens.pop(0)
			if tokens[0] == 'vertex':
				x= map( lambda x : float(x), tokens[1:4] )
				print "\tvertex %f %f %f" % ( x[0]+dx, x[1]+dy, x[2]+dz )
			else:
				sys.stdout.write( orgline )
		else:
			sys.stdout.write( orgline )
	ifile.close()

def STLcenter( filename ):
	bbox = STLbbox( filename )
	return [ 0.5*(bbox[0]+bbox[3]), 0.5*(bbox[1]+bbox[4]), 0.5*(bbox[2]+bbox[5]) ]

if __name__ == '__main__':
	if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
		print help % sys.argv[0]
		sys.exit(0)

	if len(sys.argv) == 2:
		bbox = STLbbox( sys.argv[1] )
		print "BBox: ",bbox
		print "Center: [%f %f %f]" % ( 0.5*(bbox[0]+bbox[3]), 0.5*(bbox[1]+bbox[4]), 0.5*(bbox[2]+bbox[5]) )

	if len(sys.argv) == 6 and sys.argv[2] == '-tr':
		STLtranslate( sys.argv[1], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]) )

				

