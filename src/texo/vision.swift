import Foundation
import Vision

do {
    guard #available(macOS 13.0, *) else {
        throw NSError(domain: "Texo", code: 1, userInfo: [NSLocalizedDescriptionKey: "中文识别需要 macOS 13 或更新版本。"])
    }
    guard CommandLine.arguments.count == 2 else {
        throw NSError(domain: "Texo", code: 2, userInfo: [NSLocalizedDescriptionKey: "请提供一张图片的路径。"])
    }
    let request = VNRecognizeTextRequest()
    request.revision = VNRecognizeTextRequestRevision3
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
    request.usesLanguageCorrection = false
    let supported = try request.supportedRecognitionLanguages()
    guard request.recognitionLanguages.allSatisfy({ supported.contains($0) }) else {
        throw NSError(domain: "Texo", code: 3, userInfo: [NSLocalizedDescriptionKey: "当前系统的 Vision 不支持所需的中文识别语言。"])
    }
    try VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1]), options: [:]).perform([request])
    let lines = (request.results ?? []).compactMap { observation -> [String: Any]? in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let text = candidate.string
        let box = observation.boundingBox
        let chars = text.indices.map { index -> [String: Any] in
            guard let characterBox = try? candidate.boundingBox(for: index..<text.index(after: index)) else {
                return ["text": String(text[index]), "box": [0.0, 0.0, 0.0, 0.0]]
            }
            let rect = characterBox.boundingBox
            return ["text": String(text[index]), "box": [rect.minX, rect.minY, rect.width, rect.height]]
        }
        return ["text": text, "box": [box.minX, box.minY, box.width, box.height], "chars": chars]
    }
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: lines, options: [.sortedKeys]))
} catch {
    FileHandle.standardError.write(Data("中文识别失败：\(error.localizedDescription)\n".utf8))
    exit(1)
}
