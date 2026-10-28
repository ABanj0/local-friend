use std::{fs::{self, OpenOptions}, io::{self, Write}, path::Path};

/// Publish a complete default config only if the destination is still absent.
pub fn initialize(config: &Path, template: &Path) -> io::Result<()> {
    if config.exists() { return Ok(()); }
    let staging = config.with_file_name(format!(".config-{}.tmp", uuid::Uuid::new_v4()));
    let mut file = OpenOptions::new().write(true).create_new(true).open(&staging)?;
    let outcome = (|| {
        file.write_all(&fs::read(template)?)?;
        file.sync_all()?;
        // Hard-link publication is exclusive: a concurrent user configuration wins.
        match fs::hard_link(&staging, config) {
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => Ok(()),
            result => result,
        }
    })();
    drop(file);
    let cleanup = fs::remove_file(&staging);
    outcome.and(cleanup)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Barrier};

    #[test]
    fn missing_template_leaves_no_partial_configuration() {
        let root = std::env::temp_dir().join(format!("studio-config-{}", uuid::Uuid::new_v4()));
        fs::create_dir(&root).unwrap();
        assert!(initialize(&root.join("agent.toml"), &root.join("missing.toml")).is_err());
        assert_eq!(fs::read_dir(&root).unwrap().count(), 0);
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn preserves_existing_configuration_even_without_a_template() {
        let root = std::env::temp_dir().join(format!("studio-config-{}", uuid::Uuid::new_v4()));
        fs::create_dir(&root).unwrap();
        let config = root.join("agent.toml");
        fs::write(&config, "user settings").unwrap();
        initialize(&config, &root.join("missing.toml")).unwrap();
        assert_eq!(fs::read_to_string(&config).unwrap(), "user settings");
        fs::remove_file(config).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn concurrent_first_launch_publishes_one_complete_config() {
        let root = std::env::temp_dir().join(format!("studio-config-{}", uuid::Uuid::new_v4()));
        fs::create_dir(&root).unwrap();
        let template = root.join("template.toml");
        let config = root.join("agent.toml");
        let contents = "default settings\n".repeat(10_000);
        fs::write(&template, &contents).unwrap();
        let barrier = Arc::new(Barrier::new(3));
        let handles: Vec<_> = (0..2).map(|_| {
            let (config, template, barrier) = (config.clone(), template.clone(), barrier.clone());
            std::thread::spawn(move || { barrier.wait(); initialize(&config, &template).unwrap(); })
        }).collect();
        barrier.wait();
        for handle in handles { handle.join().unwrap(); }
        assert_eq!(fs::read_to_string(&config).unwrap(), contents);
        assert_eq!(fs::read_dir(&root).unwrap().count(), 2);
        fs::remove_file(config).unwrap();
        fs::remove_file(template).unwrap();
        fs::remove_dir(root).unwrap();
    }
}
