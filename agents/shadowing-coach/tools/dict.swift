// 맥에 들어 있는 뉴에이스 영한사전에서 단어 항목을 찾는다. 인터넷·AI 없음.
// 사용: dict-lookup <단어>  → JSON 배열 [{"t": 표제어, "html": 항목 HTML}] (없으면 [])
// 기본형도 사전이 알아서 찾아 준다 (stories → story, closest → close)
import Foundation
import CoreServices

typealias CopyAvail = @convention(c) () -> Unmanaged<CFSet>?
typealias GetName = @convention(c) (AnyObject) -> Unmanaged<CFString>?
typealias CopyRecs = @convention(c) (AnyObject, CFString, UnsafeRawPointer?, UnsafeRawPointer?) -> Unmanaged<CFArray>?
typealias RecStr = @convention(c) (AnyObject) -> Unmanaged<CFString>?
typealias RecData = @convention(c) (AnyObject, Int) -> Unmanaged<CFString>?

guard let h = dlopen("/System/Library/Frameworks/CoreServices.framework/Frameworks/DictionaryServices.framework/DictionaryServices", RTLD_NOW) else { exit(2) }
func sym<T>(_ n: String, _ t: T.Type) -> T? { dlsym(h, n).map { unsafeBitCast($0, to: t) } }
guard let copyAvail = sym("DCSCopyAvailableDictionaries", CopyAvail.self),
      let getName = sym("DCSDictionaryGetName", GetName.self),
      let copyRecs = sym("DCSCopyRecordsForSearchString", CopyRecs.self),
      let headword = sym("DCSRecordGetHeadword", RecStr.self),
      let recData = sym("DCSRecordCopyData", RecData.self) else { exit(2) }

guard CommandLine.arguments.count > 1 else { exit(2) }
let word = CommandLine.arguments[1]
let dicts = (copyAvail()?.takeRetainedValue() as? Set<AnyHashable> ?? []).map { $0 as AnyObject }
guard let d = dicts.first(where: { (getName($0)?.takeUnretainedValue() as String? ?? "").contains("영한") }) else {
    print("[]"); exit(3)
}
let recs = copyRecs(d, word as CFString, nil, nil)?.takeRetainedValue() as? [AnyObject] ?? []
var out: [[String: String]] = []
for r in recs.prefix(12) {
    let t = headword(r)?.takeUnretainedValue() as String? ?? ""
    var html = recData(r, 0)?.takeRetainedValue() as String? ?? ""
    if let b = html.range(of: "<body>"), let e = html.range(of: "</body>") { html = String(html[b.upperBound..<e.lowerBound]) }
    out.append(["t": t, "html": html])
}
let data = try JSONSerialization.data(withJSONObject: out)
FileHandle.standardOutput.write(data)
