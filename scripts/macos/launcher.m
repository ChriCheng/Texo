#import <AppKit/AppKit.h>
#include <Python.h>
#include <unistd.h>

int main(int argc, char **argv) {
    @autoreleasepool {
        NSBundle *bundle = NSBundle.mainBundle;
        NSString *project = [bundle objectForInfoDictionaryKey:@"TexoProjectRoot"];
        NSString *python = [project stringByAppendingPathComponent:@".venv/bin/python"];
        NSString *script = [project stringByAppendingPathComponent:@"main.py"];
        NSFileManager *files = NSFileManager.defaultManager;
        if (!project.isAbsolutePath || ![files isExecutableFileAtPath:python] || ![files fileExistsAtPath:script]) {
            NSAlert *alert = [[NSAlert alloc] init];
            alert.messageText = @"无法启动 Texo";
            alert.informativeText = @"本机项目目录或 Python 环境已移动、删除。请在 Texo 项目中重新运行 build_macos_app.py 安装应用。";
            [alert runModal];
            return 1;
        }
        if (chdir(project.fileSystemRepresentation) != 0) {
            return 1;
        }
        setenv("TEXO_APP_BUNDLE", bundle.bundlePath.fileSystemRepresentation, 1);
        if (argc == 1) {
            NSString *logs = [project stringByAppendingPathComponent:@".local"];
            [files createDirectoryAtPath:logs withIntermediateDirectories:YES attributes:nil error:nil];
            NSString *log = [logs stringByAppendingPathComponent:@"texo-app.log"];
            freopen(log.fileSystemRepresentation, "a", stdout);
            freopen(log.fileSystemRepresentation, "a", stderr);
            setvbuf(stdout, NULL, _IONBF, 0);
        }
        // Keep Python in this process so macOS associates the window and permissions with Texo.app.
        char **arguments = calloc(argc + 2, sizeof(char *));
        if (!arguments) {
            return 1;
        }
        arguments[0] = (char *)python.fileSystemRepresentation;
        arguments[1] = (char *)script.fileSystemRepresentation;
        for (int index = 1; index < argc; index++) {
            arguments[index + 1] = argv[index];
        }
        int result = Py_BytesMain(argc + 1, arguments);
        free(arguments);
        if (result != 0 && argc == 1) {
            NSAlert *alert = [[NSAlert alloc] init];
            alert.messageText = @"Texo 启动失败";
            alert.informativeText = [@"请检查项目环境。诊断日志：" stringByAppendingString:[project stringByAppendingPathComponent:@".local/texo-app.log"]];
            [alert runModal];
        }
        return result;
    }
}
