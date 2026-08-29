
using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'artem' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'artem'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'artem' {
            [CompletionResult]::new('-c', 'c', [CompletionResultType]::ParameterName, 'Change the characters that are used to display the image.The first character should have the highest ''darkness'' and the last should have the least (recommended to be a space '' ''). A lower detail map is recommend for smaller images. Included characters can be used with the argument 0 | 1 | 2. If no characters are passed in, the default set will be used.')
            [CompletionResult]::new('--characters', 'characters', [CompletionResultType]::ParameterName, 'Change the characters that are used to display the image.The first character should have the highest ''darkness'' and the last should have the least (recommended to be a space '' ''). A lower detail map is recommend for smaller images. Included characters can be used with the argument 0 | 1 | 2. If no characters are passed in, the default set will be used.')
            [CompletionResult]::new('-s', 's', [CompletionResultType]::ParameterName, 'Change the size of the output image. The minimum size is 20. Lower values will be ignored and changed to 20. This argument is conflicting with --width and --height.')
            [CompletionResult]::new('--size', 'size', [CompletionResultType]::ParameterName, 'Change the size of the output image. The minimum size is 20. Lower values will be ignored and changed to 20. This argument is conflicting with --width and --height.')
            [CompletionResult]::new('--ratio', 'ratio', [CompletionResultType]::ParameterName, 'Change the ratio between height and width, since ASCII characters are a bit higher than long. The value has to be between 0.1 and 1.0. It is not recommend to change this setting.')
            [CompletionResult]::new('-o', 'o', [CompletionResultType]::ParameterName, 'Output file for non-colored ascii. If the output file is a plaintext file, no color will be used. The use color, either use a file with an .ansi extension, or an .svg/.html file, to convert the output to the respective format. .ansi files will consider environment variables when creating colored output, for example when COLORTERM is not set to truecolor,the resulting file will fallback to 8-bit colors.')
            [CompletionResult]::new('--output', 'output', [CompletionResultType]::ParameterName, 'Output file for non-colored ascii. If the output file is a plaintext file, no color will be used. The use color, either use a file with an .ansi extension, or an .svg/.html file, to convert the output to the respective format. .ansi files will consider environment variables when creating colored output, for example when COLORTERM is not set to truecolor,the resulting file will fallback to 8-bit colors.')
            [CompletionResult]::new('--verbose', 'verbose', [CompletionResultType]::ParameterName, 'Choose the verbosity of the logging level. Warnings and errors will always be shown by default. To completely disable them, use the off argument.')
            [CompletionResult]::new('--height', 'height', [CompletionResultType]::ParameterName, 'Use the terminal maximum terminal height to display the image. This argument is conflicting with --size and --width.')
            [CompletionResult]::new('-w', 'w', [CompletionResultType]::ParameterName, 'Use the terminal maximum terminal width to display the image. This argument is conflicting with --size and --height.')
            [CompletionResult]::new('--width', 'width', [CompletionResultType]::ParameterName, 'Use the terminal maximum terminal width to display the image. This argument is conflicting with --size and --height.')
            [CompletionResult]::new('--flipX', 'flipX', [CompletionResultType]::ParameterName, 'Flip the image along the X-Axis/horizontally.')
            [CompletionResult]::new('--flipY', 'flipY', [CompletionResultType]::ParameterName, 'Flip the image along the Y-Axis/vertically.')
            [CompletionResult]::new('--centerX', 'centerX', [CompletionResultType]::ParameterName, 'Center the image along the X-Axis/horizontally in the terminal.')
            [CompletionResult]::new('--centerY', 'centerY', [CompletionResultType]::ParameterName, 'Center the image along the Y-Axis/vertically in the terminal.')
            [CompletionResult]::new('--invert', 'invert', [CompletionResultType]::ParameterName, 'Inverts the characters used for the image, so light characters will as dark ones. Can be useful if the image has a dark background.')
            [CompletionResult]::new('--background', 'background', [CompletionResultType]::ParameterName, 'Sets the background of the ascii as the color. This will be ignored if the terminal does not support truecolor. This argument is mutually exclusive with the no-color argument.')
            [CompletionResult]::new('--border', 'border', [CompletionResultType]::ParameterName, 'Adds a decorative border surrounding the ascii image. This will make the image overall a bit smaller, since it respects the user given size.')
            [CompletionResult]::new('--no-color', 'no-color', [CompletionResultType]::ParameterName, 'Do not use color when printing the image to the terminal.')
            [CompletionResult]::new('--outline', 'outline', [CompletionResultType]::ParameterName, 'Only create an outline of the image. This uses filters, so it will take more resources/time to complete, especially on larger images. It might not produce the desired output, it is advised to use this only on images with a clear distinction between foreground and background.')
            [CompletionResult]::new('--hysteresis', 'hysteresis', [CompletionResultType]::ParameterName, 'When creating the outline use the hysteresis method, which will remove imperfection, but might not be as good looking in ascii form.This will require the --outline argument to be present as well.')
            [CompletionResult]::new('-h', 'h', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            [CompletionResult]::new('--help', 'help', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            [CompletionResult]::new('-V', 'V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', 'version', [CompletionResultType]::ParameterName, 'Print version')
            break
        }
    })

    $completions.Where{ $_.CompletionText -like "$wordToComplete*" } |
        Sort-Object -Property ListItemText
}
