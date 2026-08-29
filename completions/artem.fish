complete -c artem -s c -l characters -d 'Change the characters that are used to display the image.The first character should have the highest \'darkness\' and the last should have the least (recommended to be a space \' \'). A lower detail map is recommend for smaller images. Included characters can be used with the argument 0 | 1 | 2. If no characters are passed in, the default set will be used.' -r -f
complete -c artem -s s -l size -d 'Change the size of the output image. The minimum size is 20. Lower values will be ignored and changed to 20. This argument is conflicting with --width and --height.' -r -f
complete -c artem -l ratio -d 'Change the ratio between height and width, since ASCII characters are a bit higher than long. The value has to be between 0.1 and 1.0. It is not recommend to change this setting.' -r -f
complete -c artem -s o -l output -d 'Output file for non-colored ascii. If the output file is a plaintext file, no color will be used. The use color, either use a file with an .ansi extension, or an .svg/.html file, to convert the output to the respective format. .ansi files will consider environment variables when creating colored output, for example when COLORTERM is not set to truecolor,the resulting file will fallback to 8-bit colors.' -r -F
complete -c artem -l verbose -d 'Choose the verbosity of the logging level. Warnings and errors will always be shown by default. To completely disable them, use the off argument.' -r -f -a "{off	'Do not show logs',error	'Only show errors',warn	'Show errors and warnings',info	'Show info logs',debug	'Show debug logs',trace	'Show trace logs'}"
complete -c artem -l height -d 'Use the terminal maximum terminal height to display the image. This argument is conflicting with --size and --width.'
complete -c artem -s w -l width -d 'Use the terminal maximum terminal width to display the image. This argument is conflicting with --size and --height.'
complete -c artem -l flipX -d 'Flip the image along the X-Axis/horizontally.'
complete -c artem -l flipY -d 'Flip the image along the Y-Axis/vertically.'
complete -c artem -l centerX -d 'Center the image along the X-Axis/horizontally in the terminal.'
complete -c artem -l centerY -d 'Center the image along the Y-Axis/vertically in the terminal.'
complete -c artem -l invert -d 'Inverts the characters used for the image, so light characters will as dark ones. Can be useful if the image has a dark background.'
complete -c artem -l background -d 'Sets the background of the ascii as the color. This will be ignored if the terminal does not support truecolor. This argument is mutually exclusive with the no-color argument.'
complete -c artem -l border -d 'Adds a decorative border surrounding the ascii image. This will make the image overall a bit smaller, since it respects the user given size.'
complete -c artem -l no-color -d 'Do not use color when printing the image to the terminal.'
complete -c artem -l outline -d 'Only create an outline of the image. This uses filters, so it will take more resources/time to complete, especially on larger images. It might not produce the desired output, it is advised to use this only on images with a clear distinction between foreground and background.'
complete -c artem -l hysteresis -d 'When creating the outline use the hysteresis method, which will remove imperfection, but might not be as good looking in ascii form.This will require the --outline argument to be present as well.'
complete -c artem -s h -l help -d 'Print help (see more with \'--help\')'
complete -c artem -s V -l version -d 'Print version'
