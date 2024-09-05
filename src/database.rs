use rusqlite::{params, Connection, Result};
use crate::data::{Camouflage, InstallerError};

pub fn initialize_database(db_conn: &Connection) -> Result<(), rusqlite::Error> {
    db_conn.execute(
        "CREATE TABLE IF NOT EXISTS camouflages (
            id INTEGER PRIMARY KEY,
            vehicle_name TEXT NOT NULL,
            description TEXT,
            image_urls TEXT,
            zip_file_url TEXT NOT NULL,
            hashtags TEXT,
            file_size TEXT,
            num_downloads INTEGER,
            num_likes INTEGER,
            post_date TEXT,
            nickname TEXT
        )",
        [],
    )?;

    db_conn.execute(
        "CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )",
        [],
    )?;

    db_conn.execute(
        "CREATE TABLE IF NOT EXISTS camouflage_tags (
            camouflage_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (camouflage_id, tag_id),
            FOREIGN KEY (camouflage_id) REFERENCES camouflages(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        )",
        [],
    )?;

    Ok(())
}

pub fn update_total_camos(db_conn: &Connection) -> Result<usize, InstallerError> {
    let count: i64 = db_conn.query_row(
        "SELECT COUNT(*) FROM camouflages",
        [],
        |row| row.get(0),
    ).map_err(InstallerError::from)?; // Ensure error conversion to InstallerError
    Ok(count as usize)
}

pub fn fetch_tags(db_conn: &Connection, camouflage_id: usize) -> Result<Vec<String>, rusqlite::Error> {
    let mut stmt = db_conn.prepare(
        "SELECT t.name FROM tags t
        JOIN camouflage_tags ct ON t.id = ct.tag_id
        WHERE ct.camouflage_id = ?1"
    ).map_err(InstallerError::from)?; // Convert rusqlite::Error to InstallerError

    let tags = stmt.query_map(params![camouflage_id as i64], |row| row.get(0))
        .map_err(InstallerError::from)? // Convert rusqlite::Error to InstallerError
        .collect::<Result<Vec<String>, rusqlite::Error>>()
        .map_err(InstallerError::from)?; // Convert rusqlite::Error to InstallerError

    Ok(tags)
}

pub fn fetch_camouflage_by_index(db_conn: &Connection, index: usize) -> Result<Option<(usize, Camouflage)>, InstallerError> {
    let mut stmt = db_conn.prepare(
        "SELECT rowid, vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date, nickname
        FROM camouflages
        LIMIT 1 OFFSET ?"
    )?;

    let mut rows = stmt.query(params![index])?;

    if let Some(row) = rows.next()? {
        let camo_id: usize = row.get(0)?;
        let tags = fetch_tags(db_conn, camo_id).map_err(InstallerError::from)?; // Convert error to InstallerError
        let camo = Camouflage {
            vehicle_name: row.get(1)?,
            description: row.get(2)?,
            image_urls: row.get::<_, Option<String>>(3)?
                .unwrap_or_default()
                .split(',')
                .map(String::from)
                .collect(),
            zip_file_url: row.get(4)?,
            hashtags: row.get::<_, Option<String>>(5)?
                .unwrap_or_default()
                .split(',')
                .map(String::from)
                .filter(|s| !s.is_empty())
                .collect(),
            tags,
            file_size: row.get(6)?,
            num_downloads: row.get(7)?,
            num_likes: row.get(8)?,
            post_date: row.get(9)?,
            nickname: row.get(10)?,
        };
        Ok(Some((index, camo)))
    } else {
        Ok(None)
    }
}

pub fn fetch_camouflages(db_conn: &Connection, query: Option<&str>, selected_tags: &[String]) -> Result<Vec<Camouflage>, InstallerError> {
    let mut sql = String::from(
        "SELECT DISTINCT c.rowid, c.vehicle_name, c.description, c.image_urls, c.zip_file_url, c.hashtags, c.file_size, c.num_downloads, c.num_likes, c.post_date, c.nickname
        FROM camouflages c"
    );

    let mut params: Vec<String> = Vec::new();
    let mut where_clauses = Vec::new();

    if !selected_tags.is_empty() {
        sql.push_str("
        JOIN camouflage_tags ct ON c.rowid = ct.camouflage_id
        JOIN tags t ON ct.tag_id = t.id");
        where_clauses.push(format!("t.name IN ({})", vec!["?"; selected_tags.len()].join(",")));
        params.extend(selected_tags.iter().cloned());
    }

    if let Some(q) = query {
        where_clauses.push("(c.vehicle_name LIKE ? OR c.description LIKE ?)".to_string());
        params.push(format!("%{}%", q));
        params.push(format!("%{}%", q));
    }

    if !where_clauses.is_empty() {
        sql.push_str(" WHERE ");
        sql.push_str(&where_clauses.join(" AND "));
    }

    let mut stmt = db_conn.prepare(&sql)?;

    let param_refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|p| p as &dyn rusqlite::ToSql).collect();

    let camo_iter = stmt.query_map(param_refs.as_slice(), |row| {
        let camo_id: usize = row.get(0)?;
        let tags = fetch_tags(db_conn, camo_id).map_err(InstallerError::from)?;
        Ok(Camouflage {
            vehicle_name: row.get(1)?,
            description: row.get(2)?,
            image_urls: row.get::<_, Option<String>>(3)?
                .unwrap_or_default()
                .split(',')
                .map(String::from)
                .collect(),
            zip_file_url: row.get(4)?,
            hashtags: row.get::<_, Option<String>>(5)?
                .unwrap_or_default()
                .split(',')
                .map(String::from)
                .filter(|s| !s.is_empty())
                .collect(),
            tags,
            file_size: row.get(6)?,
            num_downloads: row.get(7)?,
            num_likes: row.get(8)?,
            post_date: row.get(9)?,
            nickname: row.get(10)?,
        })
    })?;

    Ok(camo_iter.collect::<Result<Vec<_>, rusqlite::Error>>()?)
}


#[allow(dead_code)]
pub fn add_tag(db_conn: &Connection, camouflage_id: usize, tag: &str) -> Result<(), InstallerError> {
    db_conn.execute(
        "INSERT OR IGNORE INTO tags (name) VALUES (?1)",
        params![tag],
    )?;

    let tag_id: i64 = db_conn.query_row(
        "SELECT id FROM tags WHERE name = ?1",
        params![tag],
        |row| row.get(0),
    )?;

    db_conn.execute(
        "INSERT OR IGNORE INTO camouflage_tags (camouflage_id, tag_id) VALUES (?1, ?2)",
        params![camouflage_id as i64, tag_id],
    )?;

    Ok(())
}

#[allow(dead_code)]
pub fn remove_tag(db_conn: &Connection, camouflage_id: usize, tag: &str) -> Result<(), InstallerError> {
    let tag_id: i64 = db_conn.query_row(
        "SELECT id FROM tags WHERE name = ?1",
        params![tag],
        |row| row.get(0),
    )?;

    db_conn.execute(
        "DELETE FROM camouflage_tags WHERE camouflage_id = ?1 AND tag_id = ?2",
        params![camouflage_id as i64, tag_id],
    )?;

    Ok(())
}

