use std::{collections::VecDeque, io::Read, sync::{Arc, Mutex}};

pub const LIMIT: usize = 16_384;
pub type Shared = Arc<Mutex<Diagnostics>>;

#[derive(Default)]
pub struct Diagnostics {
    lines: VecDeque<String>,
    size: usize,
}

impl Diagnostics {
    pub fn push(&mut self, line: String) {
        self.size += line.len() + 1;
        self.lines.push_back(line);
        while self.size > LIMIT {
            self.size -= self.lines.pop_front().unwrap().len() + 1;
        }
    }

    pub fn text(&self) -> String {
        self.lines.iter().cloned().collect::<Vec<_>>().join("\n")
    }
}

// Conservative native diagnostics: suppress whole sensitive/overlong lines.
// The Python worker's richer streaming redactor remains the chat privacy boundary.
pub fn safe(line: &str, credential: &str) -> String {
    let lower = line.to_lowercase();
    if (!credential.is_empty() && line.contains(credential)) ||
        ["password", "passwd", "token", "secret", "bearer", "api_key", "api-key",
         "authorization", "cookie", "private key"].iter().any(|key| lower.contains(key)) {
        "[Sensitive diagnostic line omitted]".into()
    } else {
        line.chars().filter(|c| !c.is_control() || *c == '\t').collect()
    }
}

pub fn drain(mut pipe: impl Read, output: Shared, credential: String) {
    let mut chunk = [0; 1024];
    let mut line = Vec::new();
    let mut overflow = false;
    let mut private = false;
    loop {
        let count = match pipe.read(&mut chunk) { Ok(n) => n, Err(_) => 0 };
        for byte in &chunk[..count] {
            if *byte != b'\n' {
                if line.len() < 4096 { line.push(*byte); } else { overflow = true; }
                continue;
            }
            record(&output, &credential, &line, overflow, &mut private);
            line.clear(); overflow = false;
        }
        if count == 0 {
            if !line.is_empty() || overflow { record(&output, &credential, &line, overflow, &mut private); }
            return;
        }
    }
}

fn record(output: &Shared, credential: &str, bytes: &[u8], overflow: bool, private: &mut bool) {
    let line = String::from_utf8_lossy(bytes);
    if line.contains("-----BEGIN ") { *private = true; }
    let text = if overflow || *private { "[Sensitive or oversized diagnostic omitted]".into() }
               else { safe(&line, credential) };
    if line.contains("-----END ") { *private = false; }
    if let Ok(mut store) = output.lock() { store.push(text); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounded_redacted_drain_handles_long_lines_and_private_blocks() {
        let store = Shared::default();
        let input = format!("{}\npassword=canary\n-----BEGIN PRIVATE KEY-----\nhidden-body\n-----END PRIVATE KEY-----\nlaunch-credential\nhealthy\n", "x".repeat(100_000));
        drain(input.as_bytes(), store.clone(), "launch-credential".into());
        let text = store.lock().unwrap().text();
        for secret in ["canary", "hidden-body", "launch-credential"] { assert!(!text.contains(secret)); }
        assert!(text.contains("healthy"));
        assert!(text.len() < LIMIT);
    }
    #[test]
    fn keeps_recent_diagnostics_with_fixed_budget() {
        let store = Shared::default();
        drain("old line\n".repeat(100_000).as_bytes(), store.clone(), String::new());
        assert!(store.lock().unwrap().text().len() <= LIMIT);
    }
}
