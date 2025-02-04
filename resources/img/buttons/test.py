from PIL import Image
from PIL.ImageColor import getcolor, getrgb
from PIL.ImageOps import grayscale

def image_tint(src, tint='#ffffff'):
	if Image.isStringType(src):  # file path?
		src = Image.open(src)
	if src.mode not in ['RGB', 'RGBA']:
		raise TypeError('Unsupported source image mode: {}'.format(src.mode))
	src.load()

	tr, tg, tb = getrgb(tint)
	tl = getcolor(tint, "L")  # tint color's overall luminosity
	if not tl: tl = 1  # avoid division by zero
	tl = float(tl)  # compute luminosity preserving tint factors
	sr, sg, sb = map(lambda tv: tv/tl, (tr, tg, tb))  # per component
								  # adjustments
	# create look-up tables to map luminosity to adjusted tint
	# (using floating-point math only to compute table)
	luts = (tuple(map(lambda lr: int(lr*sr + 0.5), range(256))) +
			tuple(map(lambda lg: int(lg*sg + 0.5), range(256))) +
			tuple(map(lambda lb: int(lb*sb + 0.5), range(256))))
	l = grayscale(src)  # 8-bit luminosity version of whole image
	if Image.getmodebands(src.mode) < 4:
		merge_args = (src.mode, (l, l, l))  # for RGB verion of grayscale
	else:  # include copy of src image's alpha layer
		a = Image.new("L", src.size)
		a.putdata(src.getdata(3))
		merge_args = (src.mode, (l, l, l, a))  # for RGBA verion of grayscale
		luts += tuple(range(256))  # for 1:1 mapping of copied alpha values

	return Image.merge(*merge_args).point(luts)

if __name__ == '__main__':
	import os
	tints = ["#720e0e","#41799F","#72700e","#0e722c"]
	for i in range(1,4):
		inp = os.path.join("img",str(i)+".png")
		for tint in tints:
			r, g, b, alpha = inp.split()
			result = image_tint(inp, tint)
			result.putalpha(alpha)
			result.show()
			input
	print('done')