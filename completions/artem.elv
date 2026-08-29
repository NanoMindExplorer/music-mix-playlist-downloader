
use builtin;
use str;

set edit:completion:arg-completer[artem] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'artem'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'artem'= {
            cand -c 'Change the characters that are used to display the image.The first character should have the highest ''darkness'' and the last should have the least (recommended to be a space '' ''). A lower detail map is recommend for smaller images. Included characters can be used with the argument 0 | 1 | 2. If no characters are passed in, the default set will be used.'
            cand --characters 'Change the characters that are used to display the image.The first character should have the highest ''darkness'' and the last should have the least (recommended to be a space '' ''). A lower detail map is recommend for smaller images. Included characters can be used with the argument 0 | 1 | 2. If no characters are passed in, the default set will be used.'
            cand -s 'Change the size of the output image. The minimum size is 20. Lower values will be ignored and changed to 20. This argument is conflicting with --width and --height.'
            cand --size 'Change the size of the output image. The minimum size is 20. Lower values will be ignored and changed to 20. This argument is conflicting with --width and --height.'
            cand --ratio 'Change the ratio between height and width, since ASCII characters are a bit higher than long. The value has to be between 0.1 and 1.0. It is not recommend to change this setting.'
            cand -o 'Output file for non-colored ascii. If the output file is a plaintext file, no color will be used. The use color, either use a file with an .ansi extension, or an .svg/.html file, to convert the output to the respective format. .ansi files will consider environment variables when creating colored output, for example when COLORTERM is not set to truecolor,the resulting file will fallback to 8-bit colors.'
            cand --output 'Output file for non-colored ascii. If the output file is a plaintext file, no color will be used. The use color, either use a file with an .ansi extension, or an .svg/.html file, to convert the output to the respective format. .ansi files will consider environment variables when creating colored output, for example when COLORTERM is not set to truecolor,the resulting file will fallback to 8-bit colors.'
            cand --verbose 'Choose the verbosity of the logging level. Warnings and errors will always be shown by default. To completely disable them, use the off argument.'
            cand --height 'Use the terminal maximum terminal height to display the image. This argument is conflicting with --size and --width.'
            cand -w 'Use the terminal maximum terminal width to display the image. This argument is conflicting with --size and --height.'
            cand --width 'Use the terminal maximum terminal width to display the image. This argument is conflicting with --size and --height.'
            cand --flipX 'Flip the image along the X-Axis/horizontally.'
            cand --flipY 'Flip the image along the Y-Axis/vertically.'
            cand --centerX 'Center the image along the X-Axis/horizontally in the terminal.'
            cand --centerY 'Center the image along the Y-Axis/vertically in the terminal.'
            cand --invert 'Inverts the characters used for the image, so light characters will as dark ones. Can be useful if the image has a dark background.'
            cand --background 'Sets the background of the ascii as the color. This will be ignored if the terminal does not support truecolor. This argument is mutually exclusive with the no-color argument.'
            cand --border 'Adds a decorative border surrounding the ascii image. This will make the image overall a bit smaller, since it respects the user given size.'
            cand --no-color 'Do not use color when printing the image to the terminal.'
            cand --outline 'Only create an outline of the image. This uses filters, so it will take more resources/time to complete, especially on larger images. It might not produce the desired output, it is advised to use this only on images with a clear distinction between foreground and background.'
            cand --hysteresis 'When creating the outline use the hysteresis method, which will remove imperfection, but might not be as good looking in ascii form.This will require the --outline argument to be present as well.'
            cand -h 'Print help (see more with ''--help'')'
            cand --help 'Print help (see more with ''--help'')'
            cand -V 'Print version'
            cand --version 'Print version'
        }
    ]
    $completions[$command]
}
