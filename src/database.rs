// src/database.rs

use rusqlite::{params, Connection, Result};
use crate::data::{Camouflage, InstallerError};

pub fn update_total_camos(db_conn: &Connection) -> Result<usize, InstallerError> {
    let count: i64 = db_conn.query_row(
        "SELECT COUNT(*) FROM camouflages",
        [],
        |row| row.get(0),
    )?;
    Ok(count as usize)
}

// Comment out or remove this function if not needed
/*
pub fn fetch_camouflage(db_conn: &Connection, query: &str) -> Result<Option<(usize, Camouflage)>, InstallerError> {
    let mut stmt = db_conn.prepare(
        "SELECT rowid, vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date, nickname
        FROM camouflages
        WHERE vehicle_name LIKE ?1 OR description LIKE ?1
        LIMIT 1"
    )?;

    let camo_iter = stmt.query_map([format!("%{}%", query)], |row| {
        Ok((
            row.get(0)?,
            Camouflage {
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
                file_size: row.get(6)?,
                num_downloads: row.get(7)?,
                num_likes: row.get(8)?,
                post_date: row.get(9)?,
                nickname: row.get(10)?,
            }
        ))
    })?;

    Ok(camo_iter.collect::<Result<Vec<_>, rusqlite::Error>>()?.into_iter().next())
}
*/

pub fn fetch_camouflage_by_index(db_conn: &Connection, index: usize) -> Result<Option<(usize, Camouflage)>, InstallerError> {
    let mut stmt = db_conn.prepare(
        "SELECT rowid, vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date, nickname
        FROM camouflages
        LIMIT 1 OFFSET ?"
    )?;

    let mut rows = stmt.query(params![index])?;

    if let Some(row) = rows.next()? {
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

pub fn fetch_camouflages(db_conn: &Connection, query: &str) -> Result<Vec<Camouflage>, InstallerError> {
    let mut stmt = db_conn.prepare(
        "SELECT vehicle_name, description, image_urls, zip_file_url, hashtags, file_size, num_downloads, num_likes, post_date, nickname
        FROM camouflages
        WHERE vehicle_name LIKE ?1 OR description LIKE ?1"
    )?;

    let camo_iter = stmt.query_map([format!("%{}%", query)], |row| {
        Ok(Camouflage {
            vehicle_name: row.get(0)?,
            description: row.get(1)?,
            image_urls: row.get::<_, Option<String>>(2)?
                .unwrap_or_default()
                .split(',')
                .map(String::from)
                .collect(),
            zip_file_url: row.get(3)?,
            hashtags: row.get::<_, Option<String>>(4)?
                .unwrap_or_default()
                .split(',')
                .map(String::from)
                .filter(|s| !s.is_empty())
                .collect(),
            file_size: row.get(5)?,
            num_downloads: row.get(6)?,
            num_likes: row.get(7)?,
            post_date: row.get(8)?,
            nickname: row.get(9)?,
        })
    })?;

    Ok(camo_iter.collect::<Result<Vec<_>, rusqlite::Error>>()?)
}
